# Publication notices

This repository contains AEGIS orchestration code, synthetic test fixtures and
research documentation. No Apple firmware, jailbreak executable, device backup,
credential, private evidence database or raw device log is bundled.

No project license has been selected. Referenced upstream tools and documents
retain their respective licenses; their inclusion as references does not grant
rights to redistribute their binaries.

Debian installation instructions target Debian 13 and Python 3.13. Public CI
successfully installed the project, passed 172 software tests and ran the
fixture-only simulation on that platform. Windows/Python 3.12 verification also
passed. Target-host USB access and hardware behavior still require independent
verification; installing the host application does not jailbreak a device.
Hardware installation and native Linux boot on an iPad remain unverified.

Version 0.2.0 adds optional local model summaries. Generated advice is unverified,
cannot authorize device operations, and is excluded from later summary inputs.
The version-specific software and integration results are in `docs/testing.md`;
model accuracy requires a separate representative evaluation.

The encrypted-backup verification limitation remains a blocker for physical
execution with such a backup. Retain protected backups rather than weakening
them to bypass the gate. Device-modifying actions require their explicit
operator checkpoint.

Private historical reports and machine-specific paths are excluded from this
public source. Keep newly generated reports under the ignored `.aegis/` tree.
