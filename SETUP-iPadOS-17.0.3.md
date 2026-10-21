# Example AEGIS setup: Windows laptop and iPadOS 17.0.3

Prepared 21 October 2026 for AEGIS-iPad 0.1.0. This is an example deployment profile; discover the actual model, firmware and host rather than assuming the example matches another device. For installation from GitHub, start with [the Debian guide](docs/debian.md).

The intended target is the previously specified iPad seventh generation (A10). Its exact model and firmware build still need USB confirmation. Reported iPadOS 17.0.3 falls within AEGIS's reviewed firmware range, but firmware alone does not establish device eligibility.

## Which device does what

| Device or environment | Role |
|---|---|
| Laptop running Windows | Make the backup, prepare the USB, retain source and reports |
| Same laptop booted into Debian Live | Run the full AEGIS framework with direct USB access |
| iPad running 17.0.3 | USB-connected target; AEGIS itself runs on the laptop |

The implemented physical adapter requires native Linux or macOS and blocks Windows, WSL and virtual machines. Use Debian Live Xfce amd64 for the first full-framework experiment. palen1x is a separate minimal environment for upstream palera1n; it does not supply the full AEGIS development environment.

## 1. Prepare the iPad

1. Keep the current 17.0.3 firmware during preparation; do not accept an update or restore prompt.
2. Charge the iPad and leave it booted normally. Recovery or DFU mode is unnecessary for setup and identification.
3. Keep the passcode enabled and know it so you can unlock the iPad and approve trust. The upstream restrictions for A11 iPhones are not instructions for this A10 iPad.
4. Connect with a data-capable USB-A-to-Lightning cable where possible. Upstream documents DFU problems with some USB-C-to-Lightning cables.
5. Connect only this Apple device while collecting AEGIS observations.
6. Unlock the iPad and approve **Trust This Computer** when requested by the Windows or Linux host you are using.

Sources: [palera1n device and cable requirements](https://github.com/palera1n/palera1n), [Apple trust instructions](https://support.apple.com/en-us/109054).

## 2. Prepare Windows

1. Install or open **Apple Devices** from the Microsoft Store. Confirm that it shows the connected iPad.
2. Select the iPad, then **General → Back up all of the data on your iPad to this computer → Encrypt local backup → Back Up Now**.
3. Retain the backup password privately. After completion, open **Manage Backups** and confirm the new backup. Keep the backup in private storage; do not upload it with diagnostics.
4. Keep the laptop connected to power.
5. Preserve a copy of `AEGIS-portable-source.zip` that you can access after booting Linux. Use a private cloud location that you have verified in a browser, or a second storage device. Merely placing it on Windows C: is insufficient if that volume is encrypted or inaccessible from Linux.

**Actual project limitation:** AEGIS's current backup verifier rejects encrypted backups. Make and retain the protected backup anyway. Live execution requires a reviewed backup-verification solution; this setup does not resolve that implementation gap. Do not switch off encryption merely to bypass the verifier.

The historical Windows environment contained Python 3.12.14 and AEGIS, while its default PATH Python was 3.9. Check the interpreter on your own host. Apple communication utilities were absent during those checks. One later Windows `doctor` invocation did not finish within approximately 45 seconds; treat each new host's readiness as unverified until its checks finish.

Source: [Apple backup instructions](https://support.apple.com/guide/devices-windows/back-up-and-restore-your-device-mchla3c8ed03/windows). The backup restriction is verified in `src/aegis/safety/backup.py`.

## 3. Prepare and boot the spare USB

1. Back up anything on the spare USB. Writing the image erases that drive.
2. Download **Debian 13 Live Xfce, amd64** from the [official Debian Live page](https://www.debian.org/CD/live/index.html). Choose a drive larger than the image and follow Debian's linked verification instructions.
3. In Windows, use the image writer recommended by the [Debian USB guide](https://www.debian.org/CD/faq/#write-usb), such as balenaEtcher: select the downloaded ISO, select the spare USB by its size/name, then Flash.
4. Restart into the laptop's **one-time boot menu** and select the USB. The key varies by manufacturer. Choose the **Live** entry, leaving the installer unused.
5. Start with Secure Boot enabled; Debian provides a signed bootloader. No firmware setting change is prescribed here. See [Debian's boot guidance](https://www.debian.org/releases/trixie/amd64/ch03s06.en.html).
6. Connect to Wi-Fi. Download the saved source ZIP or retrieve it from your separate storage device.

A standard Live session loses installed packages, downloaded files and reports when it shuts down. Save results to private persistent storage before restarting. The image-writing process should not be assumed to leave a normal data partition for carrying the source ZIP.

## 4. Prepare AEGIS inside Linux

These commands are for the Debian terminal, not Windows PowerShell. Run one stage at a time and stop if it fails. Debian 13's Python 3.13 meets the project's minimum Python 3.12 requirement, but this combination has not yet been tested on this laptop.

Install the host tools:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip unzip libusb-1.0-0 libimobiledevice-utils irecovery usbmuxd libusbmuxd-tools
```

Extract the supplied ZIP using the file manager. Open a terminal inside the extracted `aegis-ipad` folder, the one containing `pyproject.toml` and `requirements-dev.lock`. Create a fresh Linux environment; the Windows environment cannot be reused:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m pip install pyusb==1.3.1
.venv/bin/python -m pytest -q
```

Stop and retain the error output if installation or tests fail. The source ZIP includes the existing tests; no Linux test result is claimed in advance.

Collect host diagnostics and run the simulation:

```bash
timeout 60s .venv/bin/aegis doctor > doctor.json
.venv/bin/aegis simulate > simulation.json
```

If `doctor` times out or does not produce complete JSON, treat it as a failed check. Optional analysis programs appearing as unavailable do not automatically require installation. REA/Ghidra and cross-compilers are separate later research needs, rather than prerequisites for ordinary device identification.

Package references: [Python](https://packages.debian.org/trixie/python3), [device utilities](https://packages.debian.org/trixie/libimobiledevice-utils), [irecovery](https://packages.debian.org/trixie/irecovery), [usbmuxd](https://packages.debian.org/trixie/utils/usbmuxd), [USB transport tools](https://packages.debian.org/trixie/libusbmuxd-tools).

## 5. Confirm the actual iPad

Attach only the target iPad, booted normally and unlocked. If Linux needs a new trust relationship, the normal libimobiledevice pairing workflow can be initiated with `idevicepair pair`; approve Trust on the iPad when asked. AEGIS's discovery command does not create a pairing itself.

Run:

```bash
.venv/bin/aegis discover > discovery.json
.venv/bin/aegis compatibility > compatibility.json
```

The first hardware checkpoint is:

- Exactly one target, identified as `iPad7,11` or `iPad7,12`.
- Reported firmware `17.0.3` and a freshly observed, consistent build identifier.
- Native Linux x86_64 host, with working Apple USB communication.
- Review any remaining blockers in the complete JSON output.

These commands query the device and store local evidence; they do not jailbreak it. Save the reports and `.aegis/evidence.sqlite` privately before ending the Live session. A firmware-compatibility result does not prove that the later backup, binary, permission or device-execution checks have passed.

## 6. What remains before live execution

The current AEGIS adapter expects the exact **palera1n 2.4** standalone binary for the host architecture, matching its packaged SHA-256 manifest. Its [official release](https://github.com/palera1n/palera1n/releases/tag/v2.4) supplies `palera1n-linux-x86_64` for this host class. A different release or repackaged binary may be rejected even if upstream supports the device.

Do not use this checklist as a claim that physical execution is ready. The protected-backup verification gap, any USB permissions issues, and the first Linux validation run must be resolved before an installation plan. No hardware execution or native Linux boot on the iPad has been verified by this project. The Linux USB described here runs Linux on the **laptop**.

For comparison, current upstream [Dopamine documentation](https://github.com/opa334/Dopamine) also lists an arm64 range containing 17.0.3. AEGIS currently treats it as a manual research alternative; an automated installation adapter is not implemented. The USB route above matches AEGIS's existing palera1n adapter.

## Bundle contents and verification status

The portable source and public repository contain the source, tests, configuration and documentation. Windows environments, cached bytecode, old evidence databases, private experiment reports, device backups and jailbreak binaries are excluded. A GitHub checkout replaces the ZIP-transfer step in this example.

Research and source inspection support these instructions. Windows package/PATH checks were performed; Debian booting, Linux dependency installation, device identity, backup restoreability and physical execution have not been tested in this session.
