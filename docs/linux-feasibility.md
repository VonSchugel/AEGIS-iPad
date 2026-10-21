# Native Linux feasibility: iPad 7 / A10

Assessment date: **2026-10-20**. No native Linux boot, kernel cross-build, QEMU run
or physical-device experiment was performed by AEGIS. Exact attached board and
firmware remain unknown. `aegis linux-status` returns the machine-readable dated
assessment and source ledger bundled in `aegis/data/linux.json`.

There is a credible existing porting path. The upstream kernel contains a
[J171/iPad7,11 device tree](https://github.com/torvalds/linux/blob/f47d223627f80cb7a1eb14c585fe6cb35de5e984/arch/arm64/boot/dts/apple/t8010-j171.dts).
Both the Wi-Fi J171 and cellular [J172/iPad7,12 device tree](https://github.com/torvalds/linux/blob/f47d223627f80cb7a1eb14c585fe6cb35de5e984/arch/arm64/boot/dts/apple/t8010-j172.dts)
were fetched at the same pinned mainline revision. Their existence establishes
board descriptions, not proof that the owner's unit boots or that every peripheral
works. A10 family membership does not establish interchangeable board drivers.

## Boot-chain boundary

For A10, the ordinary path is Boot ROM → iBoot → verified iPadOS kernel. Apple's
additional LLB stage applies to A9 and earlier, so it must not be copied into an
A10 diagram. The Secure Enclave has its own boot sequence.
[Apple Platform Security, published 2021-02-18](https://support.apple.com/guide/security/boot-process-for-iphone-and-ipad-devices-secb3000f149/web).

The research candidate is an approved DFU/checkm8 entry → PongoOS → m1n1 idevice
loader → Linux Image + matching DTB + initramfs.
[PongoOS](https://github.com/checkra1n/PongoOS) supplies a pre-boot environment,
not a Linux driver suite. Hoolock documents an
[m1n1 handoff](https://github.com/HoolockLinux/docs/blob/23ebe1fbc375599221553a7e1815e5de182a6b42/tutorials/SETUP_pongoOS.md).
Its guide contains prerelease instructions, bypass settings and shell examples
requiring review. They are not adopted as ordinary jailbreak commands by AEGIS.

The loader must meet the
[ARM64 entry contract](https://github.com/torvalds/linux/blob/f47d223627f80cb7a1eb14c585fe6cb35de5e984/Documentation/arch/arm64/booting.rst):
physical DTB in x0; x1-x3 zero; suitable CPU, cache, MMU, interrupt and memory
state. The [T8010 SoC description](https://github.com/torvalds/linux/blob/f47d223627f80cb7a1eb14c585fe6cb35de5e984/arch/arm64/boot/dts/apple/t8010.dtsi)
provides AIC, architectural timer and spin-table CPU descriptions, including
loader-populated release addresses. Its timer comment explicitly excludes EL2.
Do not assume a generic GIC/EL2 machine or copy memory addresses from another
Apple device. Review RAM/reserved regions and loader fixups for the exact board.

## Subsystem readiness

Statuses describe the surveyed upstream/downstream evidence. None means
independent success on this project's physical target.

| Subsystem | Readiness | Basis and limit |
|---|---|---|
| Payload entry | Supported | Documented PongoOS/m1n1 route; untested here |
| A10 DT | Supported | Pinned J171 and J172 source observed |
| AIC / timer | Supported | Mainline SoC descriptions |
| Memory / SMP handoff | Partially implemented | Loader fixups and reservations required |
| UART | Supported | Source exists; accessible console/cable unverified |
| USB device mode | Partially implemented | Downstream branch |
| Display / brightness | Partially implemented | Basic display; full display pipeline unavailable in surveyed baseline |
| GPU | Unsupported | Surveyed baseline lists TBA |
| Touch / internal storage | Experimental | Exact J172 author report, uncorroborated here |
| Power | Partially implemented | PMGR/cpufreq do not establish suspend safety |
| Initramfs | Supported | Documented route; userspace not built here |
| Wi-Fi / BT / audio / camera / cellular | Unknown | Exact-board support not established in this bounded review |

The maintained [A10 matrix](https://github.com/HoolockLinux/docs/blob/23ebe1fbc375599221553a7e1815e5de182a6b42/features/A10.md)
lists iPad 7 DT/display/buttons in 6.13 and brightness in 6.15. Its downstream
`linux-apple` terminology must be reconciled with the current `hoolock` branch.
This is a maintainer status report, not a full validation result.

A newer [J172 touch report](https://github.com/Pauli1Go/HoolockLinux-bringup-docs/blob/c9d02dbcbb37d73cffb0ce048b03308c6416d8db/docs/touch.md)
claims automatic touch, a graphical desktop and read/write NVMe rootfs using
matching Apple firmware and modified m1n1 Host Memory Buffer setup. Treat it as
**EXPERIMENTAL, low confidence** pending complete kernel-series review and independent logs.
The report limits its hardware validation to J172 and leaves suspend/full power
behavior unresolved. Its loader link redirects to `Pauli1Go/m1n1`; pinned `src/kboot.c`
contains the HMB device-tree function and call. This corroborates implementation
source, not the reported runtime outcome. The current fork postdates that report,
and no exact complete kernel patch-series revision was verified. This lead warrants investigation, not automatic storage
changes or a claim of stable desktop Linux.

## Milestones and smallest useful experiment

| Milestone | Evidence required on the owner's board | Current local result |
|---|---|---|
| A: custom payload | Exact artifact hash and fresh loader banner | Not tested |
| B: early Linux init | Board/kernel identification plus RAM, timer and AIC logs | Not tested |
| C: Linux shell | Interactive initramfs console with retained results | Not tested |
| D: usable rootfs | RAM root first; separate approval for any storage writes | Not tested |
| E: stable graphical system | Repeated boots/input/thermal/power/recovery tests | Not tested |

1. Finish exact-board/firmware discovery and pin sources. Compare mainline basic
   bring-up with Hoolock downstream drivers before selecting a kernel.
2. Cross-build a minimal kernel, DTB, loader and initramfs with a source manifest,
   configurations, build logs and artifact hashes. The
   [Hoolock build guide](https://github.com/HoolockLinux/docs/blob/23ebe1fbc375599221553a7e1815e5de182a6b42/tutorials/SETUP.md)
   identifies Linux build requirements and the A9-A11 16K example configuration.
   Use a pinned Buildroot or Alpine userspace; avoid inherited open network shells.
3. Test init/userspace under QEMU `virt` using a kernel built for that machine.
   A passing QEMU shell test says nothing about A10 AIC, USB, NVMe or touch drivers.
4. Prepare a separate reviewed **RAM-only** boot experiment with one bounded
   attempt and a working log transport. Obtain explicit device approval before
   DFU entry or loading a payload. Stop at the first failure and retain logs.
5. Advance A → B → C using independent evidence. Then evaluate framebuffer/input.
   Keep internal storage, suspend and desktop reliability as separate experiments.

The older [Sandcastle status page](https://projectsandcastle.org/status) lists
iPhone 7/7 Plus and iPod touch 7 downloadable builds. It does not establish a
universal A7-A11 or iPad 7 port. Conversely, that historical build list does not
invalidate newer Hoolock work. A jailbreak bootstrap and native Linux milestones
are separate achievements.

The recommendation would change with a reproducible exact-board boot log and a
reviewed pinned driver/loader series, or with evidence that the detected firmware
prevents the selected documented handoff. No AEGIS command performs experimental
Linux boot-chain changes, repartitioning or firmware writes.

## Evidence freshness and access gaps

Pinned source text was fetched on 2026-10-20 after the initial browser cache and
sandbox DNS failures were resolved. The GitHub API revision and the corresponding
raw file were checked together; a fresh branch head was not assumed to identify
earlier cached content.

| Repository/ref | Confirmed revision | Commit date |
|---|---|---|
| torvalds/linux master | `f47d223627f80cb7a1eb14c585fe6cb35de5e984` | 2026-10-20 |
| HoolockLinux/docs master | `23ebe1fbc375599221553a7e1815e5de182a6b42` | 2026-09-04 |
| HoolockLinux/linux hoolock | `6831bc701a6ce059e71e5aaa9488c9195bea6927` | 2026-09-03 |
| Pauli1Go bring-up report main | `c9d02dbcbb37d73cffb0ce048b03308c6416d8db` | 2026-07-14 |
| Pauli1Go/m1n1 idevice | `0ac395710d7b2ac842c734400521288c93677ebe` | 2026-08-19 |
| checkra1n/PongoOS master | `4c9b7541629234147fcc778f0ce4162482aaccef` | 2021-11-04 |

The mainline J171, J172, SoC and ARM64 boot-contract files were fetched at the
listed mainline commit. Hoolock's pinned J172 DTS was also inspected. The
[loader source](https://github.com/Pauli1Go/m1n1/blob/0ac395710d7b2ac842c734400521288c93677ebe/src/kboot.c)
contains `dt_set_nvme_hmb` and its invocation during device-tree preparation.
That current loader revision is not asserted to be the exact report-era build.
The complete touch/kernel series, matching tested firmware and independent
runtime logs remain gaps. These sources are not a full cross-build manifest and
none verifies native boot on the owner's device. Live Sandcastle/Apple pages
remain dated documentation references. The structured ledger retains questions,
revisions, observations, confidence, limitations and next investigations.
