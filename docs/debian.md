# Install AEGIS from GitHub on Debian 13

Reviewed 21 October 2026. These instructions prepare AEGIS on the **host computer**. They do not install Linux on the iPad or perform a jailbreak. [Public Debian 13/Python 3.13 CI](https://github.com/VonSchugel/AEGIS-iPad/actions/runs/39666523238) verified Python dependency installation, 172 software tests and fixture-only simulation. Actual laptop booting, Apple USB package/interface behavior and physical-device execution remain unverified. Run each command separately and stop if a stage fails.

Use native Debian 13 (trixie), installed or booted as a Live environment, with direct USB access. The implemented physical execution adapter rejects Windows, WSL and virtual machines. On a nonpersistent Live session, save the checkout and private reports to separate persistent storage before shutdown. For preparing a Live USB and retaining the existing protected backup, see [the setup guide](../SETUP-iPadOS-17.0.3.md).

## 1. Install host dependencies

Keep the iPad disconnected while installing and testing the host software. These commands install ordinary Debian packages on the computer:

```bash
sudo apt update
sudo apt install --no-install-recommends ca-certificates git python3 python3-venv libusb-1.0-0 libimobiledevice-utils irecovery usbmuxd libusbmuxd-tools usbutils openssh-client
python3 --version
```

Debian 13 supplies Python 3.13, satisfying AEGIS's Python 3.12 minimum. Debian 12's default Python 3.11 does not meet that requirement. Sources: [Debian release notes](https://www.debian.org/releases/trixie/release-notes/whats-new.en.html), [Debian python3-venv](https://packages.debian.org/trixie/python3-venv).

| Debian package | Role |
|---|---|
| `libimobiledevice-utils` | `idevice_id`, `ideviceinfo` and backup utilities |
| `irecovery` | Query recovery/DFU information; this is the Debian package name |
| `usbmuxd` | Normal-mode USB service multiplexing and packaged device rules |
| `libusbmuxd-tools` | `inetcat` and `iproxy`; AEGIS validation uses explicit USB selection |
| `libusb-1.0-0` | Native backend for optional numeric USB enumeration |
| `usbutils`, `openssh-client` | Host diagnostics and optional authenticated validation |

Package references: [libimobiledevice-utils](https://packages.debian.org/trixie/libimobiledevice-utils), [irecovery](https://packages.debian.org/trixie/irecovery), [usbmuxd](https://packages.debian.org/trixie/utils/usbmuxd), [inetcat in trixie](https://manpages.debian.org/trixie/libusbmuxd-tools/inetcat.1.en.html), [libusb runtime](https://packages.debian.org/trixie/libusb-1.0-0). Debian's `usbmuxd` package supplies rules for starting the daemon when a supported device connects; do not start additional competing copies as a routine setup step.

## 2. Clone the repository and create a Linux environment

Clone the public source repository:

```bash
git clone https://github.com/VonSchugel/AEGIS-iPad.git
cd AEGIS-iPad
git rev-parse HEAD
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements-dev.lock pyusb==1.3.1
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m pip check
```

Run pip through `.venv/bin/python`; do not use `sudo pip`, modify Debian's system Python or reuse a Windows virtual environment. Activation is optional because the commands name the environment explicitly. Python's [venv documentation](https://docs.python.org/3/library/venv.html) explains this isolation.

The requirements file pins dependency **versions**, not artifact hashes or the Debian package snapshot. Record the checked-out commit and installed versions when reproducing an experiment. The wheel-only install intentionally fails if an appropriate published binary distribution is unavailable; stop and investigate that error instead of silently adding a Rust/compiler toolchain or changing pins.

For standard CPython 3.13, pinned `pydantic-core==2.33.2` publishes manylinux wheels for x86_64 and aarch64, and `pytest-asyncio==1.0.0` lists Python 3.13 support. These upstream facts support attempting installation; they do not establish that AEGIS passes on Debian. Sources: [pydantic-core release files](https://pypi.org/project/pydantic_core/2.33.2/#files), [pytest-asyncio 1.0.0](https://pypi.org/project/pytest-asyncio/1.0.0/).

## 3. Verify the software without a device

Create private local reports, then run the full test suite and simulation:

```bash
umask 077
mkdir -p .aegis/reports
git rev-parse HEAD > .aegis/reports/source-commit.txt
.venv/bin/python -m pip freeze > .aegis/reports/python-packages.txt
dpkg-query -W python3 python3-venv libusb-1.0-0 libimobiledevice-utils irecovery usbmuxd libusbmuxd-tools > .aegis/reports/debian-packages.txt
.venv/bin/python -m pytest -q -W error --junitxml=.aegis/reports/debian-tests.xml
.venv/bin/aegis simulate > .aegis/reports/simulation.json
timeout 60s .venv/bin/aegis doctor > .aegis/reports/doctor.json
.venv/bin/python -m json.tool .aegis/reports/doctor.json > /dev/null
```

Tests must finish successfully. A simulation must identify itself as simulated. If the timeout command exits 124 or doctor output is incomplete, retain the failure and resolve it before proceeding. Review doctor for the actual host and installed tools. Missing optional reverse-engineering applications do not prevent initial device identification; their availability is assessed separately in [the toolchain guide](toolchain.md).

The test counts in [testing.md](testing.md) distinguish Windows and Debian CI. A new local test result establishes what passed on this machine. Fixture success cannot satisfy a physical-device precondition.

## 4. Perform read-only identification

Attach only the owner's authorized iPad, booted normally and unlocked, using a data-capable cable. The discovery adapter avoids automatic pairing. If a new trust relationship is required, stop and explicitly approve that separate device-changing preparation before following the upstream pairing procedure.

```bash
timeout 60s .venv/bin/aegis discover > .aegis/reports/discovery.json
.venv/bin/python -m json.tool .aegis/reports/discovery.json > /dev/null
timeout 60s .venv/bin/aegis compatibility > .aegis/reports/compatibility.json
```

Review the reports for exactly one identified device, actual `ProductType`, actual firmware/build and every blocker. The intended model identifiers are `iPad7,11` and `iPad7,12`; their presence must be observed. A USB descriptor or a reported firmware version alone is insufficient. A tool, permission or transport failure means **unknown**, not proof of incompatibility or device absence.

If USB access fails, read the recorded error and inspect the installed Debian device rules and service state before changing permissions. Do not make USB nodes globally writable or run the whole application as root to hide an unresolved discovery problem. `lsusb -d 05ac:` can provide a basic host observation, but it does not identify the model or installed firmware.

## 5. Stop at the device approval boundary

Installing the Python application does not download or execute palera1n. Review [compatibility](compatibility.md), [recovery](recovery.md), [validation](validation.md) and [the threat model](threat-model.md) before constructing a physical experiment. The current live adapter requires the specific reviewed binary and digest, a matching verified backup, a supported native host, complete device evidence and fresh explicit operator approval.

The current backup verifier rejects encrypted backups. Retain the protected backup; resolve that verification limitation before execution instead of disabling encryption to bypass a gate. No DFU entry, payload upload, installation, reboot, firmware rewrite, erase or restore is authorized by this setup procedure.

Keep `.aegis/`, backups, identifiers, SSH keys and unreviewed device logs private. Public GitHub issues should contain only deliberately reviewed, redacted findings. Preserve private reports before ending a Live session. Successful host installation or jailbreak completion would still not establish native Linux support on the iPad; see [the separate Linux feasibility report](linux-feasibility.md).
