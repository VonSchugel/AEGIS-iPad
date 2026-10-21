"""Offline, dated Linux evidence; never boots or modifies a device."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


class LinuxResearchAgent:
    def assess(self) -> dict[str, Any]:
        """Return an independent copy of the bundled, explicitly scoped findings."""
        return json.loads(files("aegis").joinpath("data/linux.json").read_text(encoding="utf-8"))
