# Toolchain evaluation

Assessment date: 2026-10-20. Original PATH/package observations are summarized in [environment.md](environment.md); private reports are excluded from the public source. Source documentation establishes a tool's intended role; it does not establish that the installed host can execute it. No absent native tool was silently replaced or installed.

| Tool or family | Decision and implemented boundary | Current local evidence |
|---|---|---|
| Python 3.12+, asyncio, Pydantic, Click, pytest, Git | Typed evidence, bounded subprocesses, structured CLI, fixtures and local repository | Used and tested; versions locked |
| [libimobiledevice](https://github.com/libimobiledevice/libimobiledevice) | `idevice_id -l`, simple non-pairing `ideviceinfo -s` product queries | Adapter tested with fixtures; utility absent |
| [libirecovery](https://github.com/libimobiledevice/libirecovery) | Query only `irecovery -q`; never infer installed firmware from boot mode | Adapter tested with fixtures; utility absent |
| [libusbmuxd](https://github.com/libimobiledevice/libusbmuxd) | Explicit USB-only `inetcat -u … -l PORT` transport for independently pinned SSH | Mocked validation tests; utility absent |
| [libusb](https://libusb.info/) / [PyUSB](https://github.com/pyusb/pyusb) | Optional numeric Apple USB enumeration in a bounded worker; no configuration, interface claim, detach or reset | PyUSB absent; Windows numeric PnP fallback observed |
| [palera1n](https://github.com/palera1n/palera1n/releases/tag/v2.4) | Only selected physical adapter; pinned stable hashes, rootless command, single approval-bound invocation | Checksums/source verified; no executable or physical run |
| [Dopamine](https://github.com/opa334/Dopamine) | Firmware-dependent manual alternative; no automatic installation adapter | Dated compatibility snapshot; not tested |
| [checkra1n](https://checkra.in/) / [checkm8 research](https://github.com/axi0mX/ipwndfu) | Historical chain and boot-ROM evidence; neither used as a universal compatibility oracle | Documentation/source research only |
| [REA](https://github.com/morluto/rea) | Separate offline artifact admission, advertised-tool selector and strict MCP evidence parser | No connected server/CLI/provider; deep analysis blocked |
| [Ghidra](https://github.com/NationalSecurityAgency/ghidra) | Preferred candidate for supported native static analysis when binary-specific evidence is needed | Not installed/verified; no target binary supplied |
| [Rizin](https://github.com/rizinorg/rizin) / [radare2](https://github.com/radareorg/radare2) | Alternative disassembly providers, selected by artifact/host capability rather than an assumed replacement | No executable found |
| [LLVM tools](https://llvm.org/docs/CommandGuide/) | Stable object-header/symbol inspection and cross-build utilities when available | No executable found |
| [LIEF](https://lief.re/) / [Capstone](https://www.capstone-engine.org/) | Optional full format parser/disassembler dependencies; current header inspector deliberately makes narrower claims | Extras declared; not installed or used |
| [Frida](https://frida.re/docs/home/) | Separately authorized runtime instrumentation, only after compatible on-device runtime/interface exists | No session, agent or package used |
| [PongoOS](https://github.com/checkra1n/PongoOS) | Research bootloader interface; custom payload and Linux experiments kept separate from installation | Source research only; no payload sent |
| [Linux ARM64](https://www.kernel.org/doc/html/latest/arch/arm64/booting.html) | Match target DT, entry requirements and drivers; use pinned mainline/downstream sources | Device-specific research; no kernel built/booted |
| Cross GCC/Clang, DT compiler | Required before reproducing the selected downstream boot path; do not assume host compiler targets ARM64 | No cross compiler or DT build verified |
| [Buildroot](https://buildroot.org/docs.html) / [Alpine](https://wiki.alpinelinux.org/wiki/Architectures) | Small initramfs/rootfs candidate after UART/USB kernel logs and target DT are established | No rootfs built; architecture availability is not device support |
| [QEMU ARM](https://www.qemu.org/docs/master/system/target-arm.html) | Generic ARM64 initramfs/entry smoke tests only; cannot validate an A10 board without its emulated devices | No emulator found or executed |

Prefer a minimal downstream-supported serial/USB logging experiment before a graphical rootfs. Generic QEMU success would validate some userspace/build behavior and cannot establish physical A10 drivers, power management or boot compatibility. Compare Buildroot's controlled small image with Alpine's convenient packages only after the actual boot interface is reproducible.

The repository evaluates optional tools without pretending they were integrated or tested as live providers. Installation of a heavyweight engine or cross-toolchain has no current target artifact/physical-host justification; source analysis and bounded fixtures make independent progress. Version-specific source citations and access gaps are recorded in the compatibility, REA and Linux reports.
