import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone, timedelta

DURATION = re.compile(r"^P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)W)?(?:(\d+)D)?$")
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_validity(iso_duration):
    m = DURATION.match(iso_duration or "P30D")
    if not m:
        return timedelta(days=30)
    y, mo, w, d = (int(x) if x else 0 for x in m.groups())
    return timedelta(days=y * 365 + mo * 30 + w * 7 + d)


def build_record(control, verdict, payload_bytes, sensor):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    valid_until = now + parse_validity(control.evidence_validity)
    return {
        "evidence_id": f"ev_{uuid.uuid4().hex[:24]}",
        "control_id": control.id,
        "framework_refs": control.framework_refs(),
        "status": verdict["status"],
        "source": {
            "sensor": sensor,
            "query": f"opa eval data.{control.rego_packages[0]}.deny" if control.rego_packages else None,
        },
        "collected_at": now.isoformat().replace("+00:00", "Z"),
        "valid_until": valid_until.isoformat().replace("+00:00", "Z"),
        "fingerprint": "sha256:" + hashlib.sha256(payload_bytes).hexdigest(),
        "verdict_detail": {"findings": verdict.get("findings", [])},
    }


class LockerClient:
    def __init__(self, out_dir="evidence/out", push=False, bucket="evidence"):
        self.out_dir = out_dir
        self.push = push
        self.bucket = bucket

    def put(self, record):
        os.makedirs(self.out_dir, exist_ok=True)
        local_path = self._put_local(record)
        version_id = None
        if self.push:
            try:
                version_id = self._put_minio(record)
            except Exception as e:
                version_id = f"<push-failed: {e}>"
        return {"local_path": local_path, "version_id": version_id}

    def _put_local(self, record):
        ctrl = record["control_id"]
        path = os.path.join(self.out_dir, ctrl, record["evidence_id"] + ".json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(record, fh, indent=2, sort_keys=True)
        return path

    def _put_minio(self, record):
        if shutil.which("docker") is None:
            raise RuntimeError("docker not available")
        key = f"{record['control_id']}/{record['evidence_id']}.json"
        with tempfile.TemporaryDirectory() as tmp:
            payload = os.path.join(tmp, "rec.json")
            with open(payload, "w") as fh:
                json.dump(record, fh, separators=(",", ":"))
            script = (
                "mc alias set local http://minio:9000 minioadmin minioadmin >/dev/null 2>&1 "
                f"&& mc pipe local/{self.bucket}/{key} < /ev/rec.json "
                f"&& mc ls --versions --json local/{self.bucket}/{key}"
            )
            proc = subprocess.run(
                ["docker", "compose", "run", "--rm", "--no-deps",
                 "-v", f"{tmp}:/ev", "--entrypoint", "/bin/sh",
                 "locker-init", "-c", script],
                capture_output=True, text=True, cwd=_REPO_ROOT,
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
            for line in proc.stdout.splitlines():
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("version", {}).get("isDeleteMarker"):
                    continue
                return obj.get("versionId")
        return None
