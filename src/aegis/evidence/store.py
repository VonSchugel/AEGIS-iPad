"""Append-only SQLite evidence, events and JSONL export. Public exports redact IDs."""
import json
from pathlib import Path
import re
import sqlite3
import os
from uuid import uuid4

from aegis.models.core import utcnow
from aegis.models import Evidence

PRIVATE_KEYS = {"udid", "ecid", "serial", "serialnumber", "uniquechipid", "uniquedeviceid",
                "device_token", "token_scope", "password", "credential", "authorization"}


def redact(value):
    if isinstance(value, dict):
        safe = {"sha256", "manifest_digest", "digest", "revision", "source_url", "artifact_sha256", "plan_digest", "stdout_sha256", "stderr_sha256"}
        return {str(k): ("[REDACTED]" if str(k).lower().replace("_", "") in
                {x.replace("_", "") for x in PRIVATE_KEYS} else v if str(k) in safe and isinstance(v, str) else redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"(?i)\b(?:UDID|ECID|SERIAL(?:NUMBER)?|UniqueDeviceID)\s*[:=]\s*\S+", "[REDACTED IDENTIFIER]", value)
        return re.sub(r"(?i)(?<![a-z0-9])[0-9a-f]{16,64}(?![a-z0-9])", "[REDACTED DIGEST/ID]", value)
    return value


class EvidenceStore:
    def __init__(self, path: Path | str = ":memory:"):
        self.path = None if str(path) == ":memory:" else Path(path)
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.execute("CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, kind TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL)")
        self.run_id = str(uuid4())

    def add(self, kind: str, payload: dict) -> int:
        # Private device identifiers are not even retained in the local evidence database.
        encoded = json.dumps(redact(payload), sort_keys=True, ensure_ascii=True)
        with self.conn:
            cur = self.conn.execute("INSERT INTO records(run_id,kind,created_at,payload) VALUES(?,?,?,?)", (self.run_id, kind, utcnow(), encoded))
        return int(cur.lastrowid)

    def add_evidence(self, evidence: Evidence | dict) -> int:
        item = evidence if isinstance(evidence, Evidence) else Evidence.model_validate(evidence)
        return self.add("evidence", item.model_dump(mode="json"))

    def has_ids(self, ids: list[int]) -> bool:
        return bool(ids) and all(self.conn.execute("SELECT 1 FROM records WHERE id=? AND run_id=?", (i, self.run_id)).fetchone() for i in ids)

    def retain_private_log(self, name: str, content: str) -> bool:
        """Raw tool logs never enter report records or public JSONL exports."""
        if self.path is None:
            return False
        if name not in {"upstream-stdout", "upstream-stderr"}:
            raise ValueError("Unknown private log kind")
        folder = self.path.parent / "private" / self.run_id
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = folder / (name + ".log")
        with path.open("x", encoding="utf-8") as output:
            if os.name == "posix":
                os.chmod(path, 0o600)
            output.write(content)
        return True

    def export(self, path: Path) -> int:
        path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with path.open("w", encoding="utf-8") as output:
            for row in self.conn.execute("SELECT id,run_id,kind,created_at,payload FROM records ORDER BY id"):
                output.write(json.dumps({"id": row[0], "run_id": row[1], "kind": row[2], "created_at": row[3], "payload": json.loads(row[4])}) + "\n")
                count += 1
        return count

    def close(self):
        self.conn.close()
