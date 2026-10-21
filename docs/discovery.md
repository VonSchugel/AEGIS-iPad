# Read-only discovery

`aegis doctor` records the actual operating system, CPU architecture, processor description, CPU count, Python version, WSL status, Python package versions and utility locations on PATH. It also uses platform library lookup to check for libusb and libusbmuxd. PATH presence is availability evidence, not verification of provenance, installed version, supported drivers or a working transport. Doctor does not execute located device or research utilities; native-library resolution can consult system helper programs on some platforms.

`aegis discover` returns `host`, `devices`, `interfaces`, `selection`, `blockers` and evidence records. A normal-mode observation contains only product identifier, operating-system version, build, mode and a local pseudonymous binding. Missing tools or inaccessible services mean **unknown**, not proof that the iPad is disconnected. Multiple observed devices or multiple Apple USB descriptors block automatic selection.

## Normal-mode adapter

The adapter runs `idevice_id -l`, retains each identifier only in process memory and queries `ProductType`, `ProductVersion` and `BuildVersion` separately using `ideviceinfo -s -u <ephemeral identifier> -k <key> -x`. `plistlib` parses XML property-list values; an allowlist validates each returned property. Other fields, error text and raw output are not returned or persisted. The documented `-s` option uses a simple connection that avoids automatic pairing. It can leave properties inaccessible on locked or unpaired devices; discovery records that limitation instead of pairing the device.

Sources: [upstream ideviceinfo manual](https://github.com/libimobiledevice/libimobiledevice/blob/master/docs/ideviceinfo.1), [upstream implementation](https://github.com/libimobiledevice/libimobiledevice/blob/master/tools/ideviceinfo.c), [idevice_id implementation](https://github.com/libimobiledevice/libimobiledevice/blob/master/tools/idevice_id.c), inspected 2026-10-20. These are moving upstream references; exact installed versions are not established by PATH inspection.

The `device_token` field is SHA-256 of the lowercased normal-mode UDID, used only for local backup and approval binding. It is pseudonymous, potentially linkable information; public reports must omit it. Raw UDID, ECID, serial, IMEI, nonces and host pairing records are never public discovery outputs. The subprocess runner must not automatically log command arguments or raw discovery output.

## Recovery/DFU adapter

Only `irecovery -q` is exposed. The parser retains `PRODUCT`, `MODE`, `CPID` and `BDID` if syntactically valid. It drops all device-unique fields. It uses an explicitly reported mode rather than mapping USB product identifiers to an iPad model. Installed firmware and the normal-mode device token remain unknown. This command observes one selected upstream connection, not an enumeration of every recovery device.

Source: [upstream irecovery implementation](https://cgit.libimobiledevice.org/libirecovery.git/tree/tools/irecovery.c), inspected 2026-10-20, blob `b29332457c471d15d17623347555bf41340e5aa6`. Query output formatting varies with installed tool version; missing keys remain unknown.

## USB observations

Optional PyUSB access reads numeric vendor/product descriptors only. It never reads serial strings, claims an interface, changes a configuration, detaches a driver, sends control requests, or resets a device. On Windows, a read-only `Get-PnpDevice -PresentOnly` fallback outputs only the Apple vendor and numeric product descriptors. PnP instance identifiers never leave the local query. Apple descriptor observations alone do not prove that an iPad, or the requested iPad model, is present.

Each external device query has a timeout; there are no automatic retry loops. Normal-mode property queries are capped at 16 listed devices. Native USB backends run in an isolated subprocess so a blocked backend can be terminated. Fixture tests cover normal/recovery/DFU observations, malformed input, inaccessible properties, cancellation, timeout, missing tools, selection ambiguity and identifier redaction. These tests verify software behavior and are not physical-device experiments.

In this Windows execution environment, the filesystem sandbox blocks the loopback socket used when Python initializes an asyncio event loop. Fixture tests were therefore run outside that sandbox after automatic approval, with all physical transports mocked. This is an execution-environment limitation; the application does not override the event-loop implementation.

The current application does not change pairing, enter recovery or DFU, load a payload, erase a device or alter firmware during discovery. Firmware compatibility must be evaluated separately after an actual firmware version is read.
