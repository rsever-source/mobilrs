#!/usr/bin/env python3
"""Single, bounded report for Gemini news runs and persistent system incidents."""
import argparse
import base64
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPORT_PATH = "news_ai_log.json"
REPORT_BRANCH = "cloud-run-migration"
MAX_NEWS_RUNS = 6
INCIDENT_RETENTION_DAYS = 90
REPORT_AFTER = timedelta(hours=24)
API_ROOT = "https://api.github.com"


def _now():
    return datetime.now(timezone.utc)


def _iso(value):
    return value.isoformat()


def _parse(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _empty_report():
    return {"schema_version": 2, "news_runs": [], "system_incidents": []}


def _normalize(data):
    # Migrate the existing list of Gemini runs without dropping any recent entries.
    if isinstance(data, list):
        data = {"schema_version": 2, "news_runs": data, "system_incidents": []}
    if not isinstance(data, dict):
        data = _empty_report()
    runs = data.get("news_runs", [])
    incidents = data.get("system_incidents", [])
    if not isinstance(runs, list):
        runs = []
    if not isinstance(incidents, list):
        incidents = []
    return {
        "schema_version": 2,
        "news_runs": runs[-MAX_NEWS_RUNS:],
        "system_incidents": incidents,
    }


def _request(method, url, token, payload=None):
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "EngelliMe-System-Report",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=20) as response:
            raw = response.read()
            return response.status, json.loads(raw.decode("utf-8")) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        if exc.code in (409, 422):
            return exc.code, {"message": raw}
        raise RuntimeError(f"GitHub API {method} {url} failed: HTTP {exc.code}: {raw[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"GitHub API connection failed: {exc}") from exc


def _repo():
    repo = os.environ.get("GITHUB_REPOSITORY", "rsever-source/mobilrs")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is missing")
    return repo, token


def _read_report(repo, token):
    url = f"{API_ROOT}/repos/{repo}/contents/{REPORT_PATH}?ref={REPORT_BRANCH}"
    status, data = _request("GET", url, token)
    if status == 404:
        return _empty_report(), None
    content = base64.b64decode(data["content"]).decode("utf-8")
    return _normalize(json.loads(content)), data.get("sha")


def _write_report(repo, token, report, sha, message):
    url = f"{API_ROOT}/repos/{repo}/contents/{REPORT_PATH}"
    payload = {
        "message": message,
        "content": base64.b64encode(
            json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("ascii"),
        "branch": REPORT_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    status, result = _request("PUT", url, token, payload)
    if status in (409, 422):
        return False
    return True


def _prune(report, now):
    cutoff = now - timedelta(days=INCIDENT_RETENTION_DAYS)
    kept = []
    for incident in report["system_incidents"]:
        if incident.get("status") != "resolved":
            kept.append(incident)  # Never delete an active or not-yet-reported incident.
            continue
        resolved = _parse(incident.get("resolved_at"))
        if resolved is None or resolved >= cutoff:
            kept.append(incident)
    report["system_incidents"] = kept[-500:]


def _stable_details(value):
    # Workflow-run URLs change every check; they must not create a new commit every 30 minutes.
    return re.sub(r"\s*(?:\|\s*)?Çalışma:\s+https?://\S+", "", str(value or "")).strip()


def _set_incident(report, component, status, details, now):
    incidents = report["system_incidents"]
    active = next(
        (item for item in reversed(incidents)
         if item.get("component") == component and item.get("status") != "resolved"),
        None,
    )
    if status == "failure":
        if active is None:
            active = {
                "component": component,
                "first_seen": _iso(now),
                "status": "pending_24h",
                "details": str(details or "Failure reported without details")[:2500],
            }
            incidents.append(active)
        elif details and _stable_details(details) != _stable_details(active.get("details")):
            # Only persist changed error details, not changing run URLs every 30 minutes.
            active["details"] = str(details)[:2500]
        first_seen = _parse(active.get("first_seen")) or now
        if now - first_seen >= REPORT_AFTER and active.get("status") == "pending_24h":
            active["status"] = "reported"
            active["reported_at"] = _iso(now)
        return

    if active is None:
        return
    first_seen = _parse(active.get("first_seen")) or now
    if active.get("status") == "pending_24h" and now - first_seen < REPORT_AFTER:
        # Brief incidents are not retained in the report, keeping it compact.
        incidents.remove(active)
        return
    if active.get("status") == "pending_24h":
        # If the next observation is recovery after 24h, retain the incident as reported
        # before marking it resolved (important for once-daily OTV checks).
        active["status"] = "reported"
        active["reported_at"] = _iso(now)
    active["status"] = "resolved"
    active["resolved_at"] = _iso(now)
    if details:
        active["recovery_details"] = str(details)[:1000]


def _save_with_retry(mutator, message):
    repo, token = _repo()
    last_error = None
    for attempt in range(8):
        try:
            report, sha = _read_report(repo, token)
            before = json.dumps(report, ensure_ascii=False, sort_keys=True)
            mutator(report, _now())
            _prune(report, _now())
            after = json.dumps(report, ensure_ascii=False, sort_keys=True)
            if after == before:
                # No state changed: avoid a Git commit for every healthy 30-minute check.
                return report
            if _write_report(repo, token, report, sha, message):
                return report
            last_error = "Concurrent report update; retrying with latest SHA"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(min(1 + attempt, 5))
    raise RuntimeError(f"Could not safely update central report after retries: {last_error}")


def append_news_run(entry):
    """Atomically append one Gemini run and aggregate persistent source/item errors."""
    current_errors = {}
    for item in entry.get("source_errors", []) or []:
        source = str(item.get("source") or "").strip()
        if source:
            current_errors["news-source:" + source] = str(item.get("error") or "Source fetch failed")
    for item in entry.get("candidates", []) or []:
        if item.get("status") == "not_processed" and item.get("url"):
            import hashlib
            key = hashlib.sha256(str(item["url"]).encode("utf-8")).hexdigest()[:16]
            current_errors["news-item:" + key] = (
                str(item.get("title") or item.get("url")) + ": " +
                str(item.get("error") or "Candidate processing failed")
            )

    def mutate(report, now):
        report["news_runs"] = (report["news_runs"] + [entry])[-MAX_NEWS_RUNS:]
        for component, details in current_errors.items():
            _set_incident(report, component, "failure", details, now)
        # A source/article that no longer errors is recovered. Pending failures under 24h
        # are removed; reported incidents remain as resolved history.
        for incident in list(report["system_incidents"]):
            component = incident.get("component", "")
            if component.startswith(("news-source:", "news-item:")) and component not in current_errors:
                _set_incident(report, component, "success", "No longer failing in the latest news run", now)

    report = _save_with_retry(mutate, "Update central Gemini and system report")
    return report["news_runs"]


def _failed_step_summary(repo, token, run_id):
    if not run_id:
        return ""
    url = f"{API_ROOT}/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"
    try:
        _, data = _request("GET", url, token)
        failures = []
        for job in data.get("jobs", []):
            for step in job.get("steps", []):
                if step.get("conclusion") == "failure":
                    failures.append(f"{job.get('name', 'job')}: {step.get('name', 'unknown step')}")
        if failures:
            return "Başarısız adımlar: " + "; ".join(failures[:12])
    except Exception as exc:
        print("Başarısız adımlar okunamadı:", str(exc))
    return ""


def record_check(component, status, details=""):
    if status not in ("success", "failure"):
        raise ValueError("status must be success or failure")
    if status == "failure":
        try:
            repo, token = _repo()
            summary = _failed_step_summary(repo, token, os.environ.get("GITHUB_RUN_ID", ""))
            if summary:
                details = (str(details) + "\n" + summary).strip()
        except Exception as exc:
            print("Workflow hata ayrıntıları alınamadı:", str(exc))

    def mutate(report, now):
        _set_incident(report, component, status, details, now)

    report = _save_with_retry(mutate, f"Update system report: {component} {status}")
    matching = [x for x in report["system_incidents"] if x.get("component") == component]
    if matching:
        latest = matching[-1]
        print(json.dumps(latest, ensure_ascii=False))
    else:
        print(json.dumps({"component": component, "status": "recovered_before_24h"}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--component", required=True)
    check.add_argument("--status", choices=("success", "failure"), required=True)
    check.add_argument("--details", default="")
    args = parser.parse_args()
    record_check(args.component, args.status, args.details)


if __name__ == "__main__":
    main()
