import json
import os
from datetime import datetime, timezone

from google.cloud import storage


def _bucket_name():
    return os.environ.get("GCS_BUCKET", "").strip()


def enabled():
    return bool(_bucket_name())


def _client():
    return storage.Client()


def load_json(name):
    bucket_name = _bucket_name()
    if not bucket_name:
        return None
    try:
        blob = _client().bucket(bucket_name).blob(name)
        if not blob.exists():
            return None
        return json.loads(blob.download_as_text())
    except Exception as exc:
        print("GCS cache read failed:", repr(exc))
        return None


def save_json(name, data):
    bucket_name = _bucket_name()
    if not bucket_name:
        return False
    try:
        payload = dict(data)
        payload["cached_at"] = datetime.now(timezone.utc).isoformat()
        blob = _client().bucket(bucket_name).blob(name)
        blob.upload_from_string(
            json.dumps(payload, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
        )
        return True
    except Exception as exc:
        print("GCS cache write failed:", repr(exc))
        return False
