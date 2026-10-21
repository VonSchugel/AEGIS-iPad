"""Offline artifact admission; deep analysis stays independent of jailbreaks."""

from __future__ import annotations

import hashlib
import os
import stat
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aegis.adapters.rea import ReaAdapter


def identify_header(header: bytes, file_size: int) -> dict[str, Any]:
    """Bounded format hints, not a substitute for a format-aware analysis engine."""
    unknown: dict[str, Any] = {"format": "unknown", "architecture": None, "bits": None}
    if header[:4] == b"\x7fELF":
        if len(header) < 16 or header[4] not in (1, 2) or header[5] not in (1, 2) or header[6] != 1:
            return {**unknown, "diagnostic": "Truncated or invalid ELF identification"}
        bits = 32 if header[4] == 1 else 64
        if len(header) < (52 if bits == 32 else 64):
            return {**unknown, "diagnostic": "Truncated ELF header"}
        endian = "<" if header[5] == 1 else ">"
        machine = struct.unpack_from(endian + "H", header, 18)[0]
        return {
            "format": "ELF", "architecture": {183: "arm64", 40: "arm", 62: "x86_64", 3: "x86"}.get(machine),
            "machine": machine, "bits": bits, "byte_order": "little" if endian == "<" else "big",
        }
    magics = {
        b"\xcf\xfa\xed\xfe": ("<", 64), b"\xfe\xed\xfa\xcf": (">", 64),
        b"\xce\xfa\xed\xfe": ("<", 32), b"\xfe\xed\xfa\xce": (">", 32),
    }
    magic = bytes(header[:4])
    if magic in magics:
        endian, bits = magics[magic]
        if len(header) < (32 if bits == 64 else 28):
            return {**unknown, "diagnostic": "Truncated Mach-O header"}
        machine = struct.unpack_from(endian + "I", header, 4)[0]
        return {
            "format": "Mach-O", "architecture": {0x100000C: "arm64", 12: "arm", 0x1000007: "x86_64", 7: "x86"}.get(machine),
            "machine": machine, "bits": bits, "byte_order": "little" if endian == "<" else "big",
        }
    if header[:2] == b"MZ" and len(header) >= 64:
        offset = struct.unpack_from("<I", header, 0x3C)[0]
        if offset + 24 > len(header):
            return {**unknown, "diagnostic": "PE signature outside bounded header; needs format-aware provider"}
        if header[offset:offset + 4] != b"PE\0\0":
            return {**unknown, "diagnostic": "MZ prefix without a valid PE signature"}
        machine = struct.unpack_from("<H", header, offset + 4)[0]
        return {
            "format": "PE", "architecture": {0xAA64: "arm64", 0x1C4: "arm", 0x8664: "x86_64", 0x14C: "x86"}.get(machine),
            "machine": machine, "bits": {0xAA64: 64, 0x8664: 64, 0x1C4: 32, 0x14C: 32}.get(machine),
        }
    if header[:4] in (b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf") and len(header) >= 8:
        count = struct.unpack_from(">I", header, 4)[0]
        stride = 32 if header[3] == 0xBF else 20
        if 0 < count <= 32 and len(header) >= 8 + stride * count:
            entries = []
            for i in range(count):
                offset = 8 + stride * i
                machine = struct.unpack_from(">I", header, offset)[0]
                location, size = struct.unpack_from(">QQ" if stride == 32 else ">II", header, offset + 8)
                if not size or location < 8 + count * stride or location + size > file_size:
                    return {**unknown, "diagnostic": "Invalid fat Mach-O slice bounds"}
                entries.append({"machine": machine, "offset": location, "size": size})
            return {"format": "Mach-O universal", "architecture": None, "bits": None, "slices": entries}
        return {**unknown, "diagnostic": "Ambiguous fat Mach-O/Java prefix; no format claim"}
    if header[:4] == b"PK\x03\x04":
        return {"format": "ZIP container candidate", "architecture": None, "bits": None}
    return unknown


class ReverseEngineeringAgent:
    """Hash and identify a supplied regular file without executing its contents."""

    def __init__(self, adapter: ReaAdapter | None = None, *, max_bytes: int = 536_870_912) -> None:
        if not isinstance(max_bytes, int) or max_bytes < 1:
            raise ValueError("max_bytes must be a positive integer")
        self.adapter = adapter or ReaAdapter()
        self.max_bytes = max_bytes

    def inspect(self, path: Path) -> dict[str, Any]:
        path = Path(path)
        if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError("Artifact must be a regular file, not a link or device")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > self.max_bytes:
                raise ValueError("Artifact is not a regular file within the inspection size budget")
            digest = hashlib.sha256()
            total = 0
            header = b""
            while True:
                block = stream.read(min(1_048_576, self.max_bytes - total + 1))
                if not block:
                    break
                total += len(block)
                if total > self.max_bytes:
                    raise ValueError("Artifact grew beyond the inspection size budget")
                digest.update(block)
                if len(header) < 65_536:
                    header += block[:65_536 - len(header)]
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino) or total != after.st_size:
                raise ValueError("Artifact changed during inspection; no stable identity recorded")
        sha256 = digest.hexdigest()
        capabilities = self.adapter.capabilities()
        return {
            "status": "metadata_only",
            "classification": "VERIFIED",
            "artifact": {"name": path.name, "sha256": sha256, "size": total, **identify_header(header, total)},
            "capabilities": capabilities,
            "deep_analysis": {**self.adapter.native_analysis_plan(), "status": "blocked", "reason": "No verified native provider session has analyzed this artifact"},
            "symbols": None, "strings": None, "references": None, "call_graph": None,
            "evidence": [{
                "question": "What bytes and executable header are present in the supplied artifact?",
                "source_url": "urn:sha256:" + sha256,
                "revision": sha256,
                "observed": "SHA-256, size, and a bounded 65536-byte header; no target code executed.",
                "classification": "VERIFIED", "confidence": "high",
                "limitations": ["Header hints do not validate the entire executable or establish runtime behavior.", "No symbols, strings, references, or control-flow analysis was performed."],
                "reproduction": "Use aegis inspect --artifact with the same local artifact; compare its SHA-256.",
                "next_step": "Connect a verified REA provider and ask a focused binary-specific question.",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }],
        }
