# Verified environment — 2026-10-20

This is a summary of the original read-only Windows observations. Private environment/discovery reports and machine-specific paths are excluded from this public source. It does not describe the reader's Debian host; rerun `aegis doctor` and `aegis discover` there.

| Property | Observation |
|---|---|
| Host | Windows 11, AMD64 |
| CPU | Intel64 Family 6 Model 166 Stepping 0; 12 logical processors |
| Application runtime | Python 3.12.14 |
| Default PATH Python | Python 3.9; unsuitable for this project |
| Available relevant executables | Git, OpenSSH, PowerShell |
| Apple utilities | idevice_id, ideviceinfo, idevicebackup2, irecovery, usbmuxd, inetcat, palera1n absent from PATH |
| Analysis engines | No registered REA MCP tools; no REA, Ghidra, Rizin, LLVM inspection or Frida executable found on PATH |
| Optional binary/USB Python packages | LIEF, Capstone, PyUSB and Frida absent |
| Native Apple USB observation | Windows PnP returned no numeric Apple USB descriptors in the bounded observation |
| Identified target / firmware | UNKNOWN / UNKNOWN |

No observation is proof that no device is physically connected. Missing utilities, drivers, pairing or access can prevent identification. No pairing request or mode change was made. The live plan exits with a structured precondition failure at identification.

The build used an isolated Python 3.12.14 environment. Create a fresh environment for each host; do not reuse the Windows environment on Linux. The [Debian guide](debian.md) provides portable setup and reporting commands.

Pinned Python packages were installed into the workspace environment. No jailbreak executable, Apple firmware, Linux image or REA provider was downloaded or executed. Existing upstream documentation/source and release checksum metadata were inspected online. No proprietary artifact was provided for binary analysis.

Earlier sandbox restrictions prevented Windows asyncio from opening its local socket pair and restricted package access. Approved local test execution resolved that environment restriction; no workaround changed event-loop behavior in production code. Subsequent unrestricted runs use ordinary Python asyncio.

Next justified hardware step: use a supported native Linux/macOS host with verified Apple USB tooling, connect only the authorized target and rerun read-only discovery. Exact firmware/build and backup evidence must precede any physical installation plan. Native Linux and macOS execution paths remain untested on this Windows host.
