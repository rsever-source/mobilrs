import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import system_report as sr


class SystemReportIncidentLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)

    def test_repeated_same_source_failure_updates_one_active_incident(self):
        report = sr._empty_report()
        component = sr.TBB_SOURCE_COMPONENT

        sr._set_incident(
            report, component, "failure", "CERTIFICATE_VERIFY_FAILED",
            self.start, immediate=True,
        )
        sr._set_incident(
            report, component, "failure", "CERTIFICATE_VERIFY_FAILED",
            self.start + timedelta(hours=2), immediate=True,
        )

        self.assertEqual(len(report["system_incidents"]), 1)
        incident = report["system_incidents"][0]
        self.assertEqual(incident["first_seen"], self.start.isoformat())
        self.assertEqual(
            incident["last_seen"], (self.start + timedelta(hours=2)).isoformat()
        )
        self.assertEqual(incident["occurrences"], 2)
        self.assertEqual(incident["status"], "reported")

    def test_other_sources_success_cannot_resolve_tbb_incident(self):
        report = sr._empty_report()
        sr._set_incident(
            report, sr.TBB_SOURCE_COMPONENT, "failure",
            "CERTIFICATE_VERIFY_FAILED", self.start, immediate=True,
        )

        def save(mutator, _message):
            mutator(report, self.start + timedelta(hours=2))
            return report

        with patch.object(sr, "_save_with_retry", side_effect=save):
            sr.append_news_run({
                "run_at": (self.start + timedelta(hours=2)).isoformat(),
                "source_errors": [],
                "candidates": [],
            })

        self.assertEqual(report["system_incidents"][0]["status"], "reported")

    def test_only_explicit_tbb_success_check_resolves_tbb_incident(self):
        report = sr._empty_report()
        sr._set_incident(
            report, sr.TBB_SOURCE_COMPONENT, "failure",
            "CERTIFICATE_VERIFY_FAILED", self.start, immediate=True,
        )

        def save(mutator, _message):
            mutator(report, self.start + timedelta(hours=2))
            return report

        with patch.object(sr, "_save_with_retry", side_effect=save):
            sr.record_check(
                sr.TBB_SOURCE_COMPONENT,
                "success",
                "TBB-specific list and detail validation passed.",
                immediate=True,
            )

        incident = report["system_incidents"][0]
        self.assertEqual(incident["status"], "resolved")
        self.assertEqual(
            incident["resolved_at"], (self.start + timedelta(hours=2)).isoformat()
        )


if __name__ == "__main__":
    unittest.main()
