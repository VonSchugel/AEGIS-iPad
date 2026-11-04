# Native Linux feasibility — exact iPad 7 scope

Checked **2026-11-04**. This report supersedes the *research coverage* of the
2026-10-20 report; its physical results remain unchanged. No payload was built or
loaded, no QEMU run occurred, and no Linux boot was observed on the owner's iPad.
The connected board and firmware remain **UNKNOWN**. Revisions, content hashes,
access gaps and limitations are in [linux-sources.json](linux-sources.json).

## Decision

**HYPOTHESIS:** the smallest useful path is a reproducible, RAM-root experiment
using a pinned Hoolock kernel, exact J171/J172 DTB and compatible m1n1/PongoOS
handoff, after identity, firmware, logging and recovery readiness are established.
Keep this as a separate research workflow. A completed jailbreak cannot satisfy
a Linux milestone. Start with ordinary host-side source/configuration admission,
then an independently reviewed build; physical loading requires its own approval.

**DOCUMENTED:** mainline contains both board descriptions. **EXPERIMENTAL:** a
maintained derivative now reports substantially more J172 functionality than the
older AEGIS survey captured. Neither fact establishes reliable operation on
J171 or on the owner's unit. The decision would change if an exact-board build
manifest and fresh, reproducible boot logs demonstrate a simpler working route.

## Evidence and competing implementations

| Candidate | Evidence checked | Applicability and integration decision |
|---|---|---|
| Mainline Linux | `05441d697f7f9a927264f4058cbbc6a03dfcac9d`, 2026-11-03 | **VERIFIED source observation:** J171 and J172 DTSs identify Wi-Fi/cellular boards and include common T8010 descriptions. Prefer for small, reviewable baseline comparisons; no local boot established. |
| HoolockLinux | kernel `6831bc701a6ce059e71e5aaa9488c9195bea6927`; docs `23ebe1fbc375599221553a7e1815e5de182a6b42` | **DOCUMENTED:** downstream bring-up and USB support; A10 feature matrix distinguishes mainline, downstream, WIP and TBA. Primary reusable kernel/loader workflow. |
| Pauli1Go derivative | kernel `7b3e4e8b0156e190d9175c6fcf396ae384419f14`, 2026-10-24; m1n1 `0ac395710d7b2ac842c734400521288c93677ebe` | **EXPERIMENTAL:** author reports J172 NVMe Debian desktop, touch, battery/charging, Wi-Fi and Bluetooth. GPU/speakers/rotation remain incomplete; Bluetooth RF calibration unresolved. Review selected series before reuse; no reliability advantage independently measured. |
| Project Sandcastle | original status page | **DOCUMENTED:** downloadable hardware targets listed are iPhone 7/7 Plus and iPod touch 7. Useful historical loader/driver references; no direct iPad 7 port established by that page. |
| pomme | [project README](https://github.com/xenoaitham/pomme/blob/8a7780b8824dcad7a21730251782b5a5a4acf6e6/README.md), `8a7780b8824dcad7a21730251782b5a5a4acf6e6` | **DOCUMENTED, author-reported builds:** pinned Linux-host build pipeline and manifests, explicitly no hardware boots. Reuse provenance/build organization as a reference. Do not adopt its target or performance rankings as verification. |
| postmarketOS | HoolockRD attribution; direct wiki access failed | **UNKNOWN exact-device packaging:** HoolockRD acknowledges postmarketOS ramdisk ancestry. This review could not independently verify a current J171/J172 pmaports recipe. Do not equate shared kernel ancestry with a supported device image. |

Primary source links: [mainline J171](https://github.com/torvalds/linux/blob/05441d697f7f9a927264f4058cbbc6a03dfcac9d/arch/arm64/boot/dts/apple/t8010-j171.dts),
[J172](https://github.com/torvalds/linux/blob/05441d697f7f9a927264f4058cbbc6a03dfcac9d/arch/arm64/boot/dts/apple/t8010-j172.dts),
[Hoolock A10 matrix](https://github.com/HoolockLinux/docs/blob/23ebe1fbc375599221553a7e1815e5de182a6b42/features/A10.md),
[Pauli1Go status](https://github.com/Pauli1Go/HoolockLinux/blob/7b3e4e8b0156e190d9175c6fcf396ae384419f14/README.md),
[Sandcastle status](https://projectsandcastle.org/status).

### What was actually compared

**VERIFIED source observations**, using pinned raw files, not runtime benchmarks:

- Hoolock's `apple_z2.c` has 482 newline-delimited lines and lacks the J172
  match entry; the derivative has 2451 and includes J172-specific parsing and
  `apple,j172-touchscreen`. Line counts indicate review scope, not speed/quality.
- The derivative's `t8010-ipad7.dtsi` supplies J172-specific PCIe, touch,
  Bluetooth and power nodes. Its leaf J172 DTS is byte-equivalent in retrieved
  UTF-8 text to mainline's leaf; examining only that leaf would miss the changes.
- The derivative loader's `kboot.c` contains HMB and SysCfg setup absent from
  the surveyed Hoolock loader. This corroborates an implementation dependency;
  it does not reproduce the storage or wireless results.

See [touch driver](https://github.com/Pauli1Go/HoolockLinux/blob/7b3e4e8b0156e190d9175c6fcf396ae384419f14/drivers/input/touchscreen/apple_z2.c),
[common board source](https://github.com/Pauli1Go/HoolockLinux/blob/7b3e4e8b0156e190d9175c6fcf396ae384419f14/arch/arm64/boot/dts/apple/t8010-ipad7.dtsi),
and [loader source](https://github.com/Pauli1Go/m1n1/blob/0ac395710d7b2ac842c734400521288c93677ebe/src/kboot.c).
No whole-tree merge-base comparison, complete driver security review or fair
hardware benchmark was completed. Photographs added by the October commit are
additional author material, not independent replication.

## Boot and firmware constraints

**DOCUMENTED:** the research route is DFU/checkm8 entry → PongoOS → idevice m1n1
→ board DTB, Linux image and initramfs. Hoolock also documents an iBoot route;
it has different per-model preparation and does not justify an automatic fallback.
The [Hoolock build guide](https://github.com/HoolockLinux/docs/blob/23ebe1fbc375599221553a7e1815e5de182a6b42/tutorials/SETUP.md)
uses a 16 KiB A9–A11 example configuration and Linux kernel builds on Linux.
Its README firmware range is 9.0–18.0; that stale-looking broad statement must
be reconciled with the detected firmware and chosen loader before experimentation.

**VERIFIED source observation:** T8010 describes Apple AIC, ARM architectural
timers and spin-table secondary CPUs; release addresses need loader fixups.
Its source states EL2 is unavailable. Do not substitute a GIC/EL2 assumption.
The [ARM64 entry contract](https://docs.kernel.org/arch/arm64/booting.html) requires
the physical DTB in x0, x1–x3 zero, appropriate execution/cache/MMU/interrupt
state and valid memory reservations. Exact DTB and actual RAM fixups are gates.

**EXPERIMENTAL:** the derivative's [firmware guide](https://github.com/Pauli1Go/HoolockLinux-linux-firmware/blob/944541e67b4c603df328c77d30093551de802c17/ipad7.md)
names 18.7.9/22H355 as its tested extraction input. That does not establish
boot-chain support across that version range or the firmware on this device.
It requires matching firmware and private device-specific calibration. Retain
those files privately; never copy another device's calibration. A RAM shell
should precede storage-dependent extraction or peripheral enablement.

Hoolock's [PongoOS guide](https://github.com/HoolockLinux/docs/blob/23ebe1fbc375599221553a7e1815e5de182a6b42/tutorials/SETUP_pongoOS.md)
includes unpinned downloads, bypass settings and shell snippets. Its own examples
need review: creating a local branch named `iOS15` does not select a remote
branch; one example changes into a mismatched directory. Treat the page as
research input, never an executable AEGIS plan.

## Subsystem readiness

All **local physical results are NOT_TESTED**. “Source present” establishes
inspectable implementation, not driver completeness or board validation.

| Subsystem | J171 evidence | J172 evidence | Required acceptance on target |
|---|---|---|---|
| CPU/architecture | Mainline source present | Mainline source present | Correct board/kernel identity, execution state and secondary CPU logs |
| AIC/timers | T8010 source present | T8010 source present | Timer progresses; interrupts counted; no fatal early exceptions |
| Memory/reservations | Loader-dependent | Loader-dependent | Correct RAM bounds, loader release addresses and reserved regions |
| Device tree | Exact mainline leaf | Exact mainline leaf plus derivative common nodes | Validated bindings, exact model selection and retained fixup manifest |
| UART/USB diagnostics | Downstream/documented | Downstream/documented | Bidirectional bounded console; capture survives selected boot phase |
| Storage | Exact runtime support unknown | Experimental HMB/ANS/NVMe report | Defer internal writes; first use RAM root; separate recovery-reviewed trial |
| Display | Documented basic framebuffer | Documented framebuffer; experimental desktop report | Visible known pattern and correct dimensions; GPU assessed separately |
| Touch | Unvalidated | Experimental driver/report | Fresh automatic probe and measured evdev single/multitouch behavior |
| Power | Mainline PMGR/cpufreq descriptions | Experimental battery/charging additions | Bounded temperature/current observations; suspend separately evaluated |
| Root filesystem | Generic ARM64 capability | Experimental NVMe Debian report | Initramfs shell first; mounted RAM root, init completion and safe exit |
| Wi-Fi/Bluetooth | Exact validation unknown | Experimental derivative claims | Firmware/calibration provenance and bounded connectivity/error tests |
| GPU/audio/camera/cellular | No usable exact-board result established | GPU/speakers unfinished; camera/cellular not established | Independent device-specific work; never implied by desktop display |

Basis: [T8010 source](https://github.com/torvalds/linux/blob/05441d697f7f9a927264f4058cbbc6a03dfcac9d/arch/arm64/boot/dts/apple/t8010.dtsi),
the Hoolock matrix, derivative sources and the [J172 touch report](https://github.com/Pauli1Go/HoolockLinux-bringup-docs/blob/c9d02dbcbb37d73cffb0ce048b03308c6416d8db/docs/touch.md).

## L0–L5 acceptance and evidence separation

The machine-readable `research_milestones` field adds these six stages while
retaining legacy A–E milestones for existing callers. All six local statuses
are **NOT_TESTED**; partial source research cannot satisfy physical criteria.

| Stage | Acceptance criteria | Documented possibility | Simulation role | Local result |
|---|---|---|---|---|
| L0 hardware/boot knowledge | Read-only observed ProductType, board, firmware/build, host and boot-chain assumptions; evidence-linked gaps | Exact DTSs available | Exercise missing/mismatched identity rejection | NOT_TESTED |
| L1 control/visibility | Reviewed log transport and explicit operator-approved interface experiment; retain board-bound transport/banner evidence | PongoOS/m1n1 route | Host adapter timeout/disconnect tests only | NOT_TESTED |
| L2 payload | Approved RAM-only payload, pinned source/build/config/hash, fresh matching banner and return/recovery observation | Loader route documented | Artifact admission and plan checks only | NOT_TESTED |
| L3 early Linux | Exact kernel/DTB hashes plus target boot log demonstrating RAM, AIC/timer and early init | Source/entry contract available | QEMU tests generic kernel/userspace, never T8010 compatibility | NOT_TESTED |
| L4 shell/rootfs | Interactive RAM-root shell, recorded command results, no internal-disk dependency | Initramfs paths documented | Same init script tested on QEMU `virt` with matching `virt` kernel | NOT_TESTED |
| L5 usability | Repeated boots plus bounded display/input/thermal/power/recovery tests; storage/radio separately scoped | Partial downstream/experimental support | Regression harness can organize results, cannot confer device support | NOT_TESTED |

## Smallest experiments and build choice

**HYPOTHESIS / proposed tests**, none executed here:

1. Admit exact-board sources and configurations offline; record revisions,
   submodules, licenses, compiler versions, hashes and binding-check output.
   Success: no unresolved source/configuration references and no foreign-board
   DTB selected. Hoolock baseline first; derivative drivers reviewed separately.
2. Build a minimal ARM64 initramfs using pinned **Buildroot 2025.02.19 LTS**
   as a conservative candidate, then evaluate equivalent Alpine minirootfs only
   if a package-managed root is needed. The [current download page](https://buildroot.org/download.html)
   also offers 2026.08.1. The [Buildroot manual](https://buildroot.org/downloads/manual/manual.html)
   supports independent rootfs/toolchain generation and Linux hosts. Keep
   configuration, source cache, legal-info and final cpio metadata in the manifest.
3. Smoke-test `/init` under a pinned [QEMU `virt`](https://www.qemu.org/docs/master/system/arm/virt.html)
   machine/version with a `virt`-capable ARM64 kernel and serial console. Pass:
   init, shell, required commands and shutdown complete within a fixed deadline.
   This machine emulates generic devices; it cannot verify A10 AIC, USB, ANS or
   touch. Alpine's [user-mode cross-architecture guide](https://wiki.alpinelinux.org/wiki/How_to_make_a_cross_architecture_chroot)
   is useful for userspace packaging only and still uses the host kernel.
4. Review [HoolockRD](https://github.com/HoolockLinux/HoolockRD/blob/2dce746e1165ad81b23e354773c19795dbd6b328/README.md)
   as a reusable test-ramdisk pattern. Its shell/reboot behavior needs deliberate
   configuration. Avoid inheriting unrestricted network shells or automatic
   reboot behavior into the first observation experiment.
5. Only after L0/build/logging gates, prepare one approved RAM-only L1–L4 attempt
   with one physical USB owner, bounded duration and retained logs. Keep NVMe
   writing, repartitioning, radio calibration and suspend out of that attempt.

Asahi's [m1n1 guide](https://asahilinux.org/docs/sw/m1n1-user-guide/) contributes
build manifests, controlled handoff and modular experiments. Its Mac-specific
hypervisor, device drivers, installer and platform assumptions are not evidence
of A10 support. Select the idevice fork deliberately; current upstream m1n1
licensing and platform evolution must not be substituted for the pinned fork.

## Maintenance, licensing and access limits

The kernel COPYING/SPDX text applies per file; DT sources use their own SPDX
licenses. Hoolock idevice m1n1 is MIT at the checked revision. Hoolock docs are
MIT except bundled `Pongo.bin`, which has separate terms. `remote_boot` is
BSD-3-Clause, HoolockRD GPL-3.0. The derivative firmware-helper/documentation
repository did not advertise a license in the API; inspect its actual files and
resolve permission before incorporating code. Apple firmware is not an open
driver license and should not be redistributed by implication.

GitHub API eventually hit its shared unauthenticated rate limit; pinned raw
files remained accessible. Direct postmarketOS wiki pages failed/redirected to
an inaccessible domain; Apple Platform Security returned HTTP 429, so its earlier
boot-chain citation was not silently refreshed. Several branch/commit pages
were restricted by the browser tool. No claim of exhaustive fork coverage,
independent runtime replication or current upstream patch acceptance is made.
