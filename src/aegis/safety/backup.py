from contextlib import closing
from datetime import datetime, timezone, timedelta
import hashlib
from pathlib import Path
import plistlib
import sqlite3
import time

from aegis.models import WorkflowError


def verify_backup(folder: Path, device: dict, now: datetime | None = None) -> dict:
    """Validate a completed local Apple backup without writing or pairing with a device."""
    now = now or datetime.now(timezone.utc)
    try:
        names = ("Info.plist", "Status.plist", "Manifest.plist")
        if any((folder / name).stat().st_size > 16 * 1024 * 1024 for name in names):
            raise ValueError("Backup metadata exceeds the supported size limit")
        blobs = [(folder / name).read_bytes() for name in names]
        info, status, manifest = [plistlib.loads(b) for b in blobs]
        if not all(isinstance(value, dict) for value in (info, status, manifest)):
            raise ValueError("Backup metadata roots must be dictionaries")
        target = str(info.get("Target Identifier", "")).lower().strip()
        if not target or not device.get("device_token") or hashlib.sha256(target.encode("ascii")).hexdigest() != device["device_token"]:
            raise ValueError("Backup target does not match current device")
        if info.get("Product Type") != device.get("product_type") or info.get("Product Version") != device.get("product_version"):
            raise ValueError("Backup product or firmware differs from the current device")
        date = info.get("Last Backup Date")
        if not isinstance(date, datetime):
            raise ValueError("Backup date is absent")
        date = date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date.astimezone(timezone.utc)
        if not timedelta(0) <= now - date <= timedelta(days=7):
            raise ValueError("Backup must be completed within the last seven days")
        if status.get("SnapshotState") != "finished":
            raise ValueError("Backup snapshot is not finished")
        if manifest.get("IsEncrypted") is not False:
            raise ValueError("Encrypted backup integrity cannot be independently verified by this implementation")
        db = folder / "Manifest.db"
        hasher = hashlib.sha256(b"".join(blobs))
        with db.open("rb") as database:
            while chunk := database.read(1024 * 1024):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            deadline = time.monotonic() + 30
            connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
            connection.execute("PRAGMA query_only=ON")
            if connection.execute("PRAGMA quick_check").fetchone() != ("ok",):
                raise ValueError("Backup manifest integrity check failed")
            file_ids = connection.execute("SELECT fileID FROM Files WHERE flags=1").fetchall()
            if not file_ids:
                raise ValueError("Backup contains no regular file records")
            for (file_id,) in file_ids:
                if not isinstance(file_id, str) or len(file_id) != 40 or any(c not in "0123456789abcdef" for c in file_id):
                    raise ValueError("Invalid backup file identifier")
                if not ((folder / file_id[:2] / file_id).is_file() or (folder / file_id).is_file()):
                    raise ValueError("Backup payload files are missing")
    except (OSError, ValueError, sqlite3.Error, plistlib.InvalidFileException, UnicodeError) as exc:
        # Do not include filesystem paths or identifiers in an error report.
        raise WorkflowError("BACKUP_UNVERIFIED", "Backup verification failed", {"reason": str(exc) if isinstance(exc, ValueError) else type(exc).__name__}) from None
    return {"verified": True, "manifest_digest": digest, "backup_date": date.isoformat(), "regular_files_present": len(file_ids),
            "limitations": "Manifest quick_check and payload presence only; file contents and restoreability are not verified. Operator must review backup and accept this limit."}
