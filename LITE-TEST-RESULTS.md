# Photos Lite verification

Tested on 2026-10-25 using VirtualBox 7.2.22 on this host. The separate
`Photos-Lite-Test` VM has 2 virtual CPUs, 1024 MB RAM for the gallery test and
1536 MB for account-setup verification, 32 MB video RAM, VBoxVGA,
3D disabled, BIOS, long mode/PAE, and a PCnet-FAST III NAT adapter. Tests use fresh
RAM-backed live data; the existing `pixell` VM and its disk are preserved.

## Build

- Android-x86 9.0-r2 x86-64, Magisk 26.4, custom Pixel/sailfish identity.
- Photos 7.98.0.1001971222, original Google signature; x86-64 native libraries.
- No Play Store, Chrome, Google Search, Gmail or LSPosed. Zygisk disabled.
- Low-RAM mode, only the 64-bit app zygote, 800×600 software graphics, animations
  disabled and at most six cached app processes.
- Direct SquashFS root, with app APKs uncompressed at the filesystem layer.
- Cache-aware low-memory thresholds enabled in the Android ramdisk. The stock
  kernel has no MEMCG_SWAP; Pie's default pressure-only path repeatedly killed
  Google services while reclaimable file cache remained. The new setting avoids
  that path without disabling Android's memory manager. It does not eliminate
  memory pressure: Google services still restarted repeatedly during the fresh
  1 GB test (`build/lite/delivered-1gb-logcat.txt`). Account setup needs more RAM.

## Scope

Local-gallery tests use one 640×480 JPEG copied into the test guest and indexed
by MediaProvider. The JPEG and test account state are not included in the ISO.
Memory figures are proportional set size (PSS) from `dumpsys meminfo`; kernel
available memory is from `/proc/meminfo`. Neither predicts a large cloud library.

The Google account email/phone page can be checked without credentials. No real
account password, completed authentication, cloud backup or unlimited-storage
entitlement has been tested. EFI, VMware, disk-install persistence, Raspberry Pi
hardware, large libraries and optional editing models have not been tested here.

An earlier compressed-APK candidate stalled during sign-in at 1 GB and generated
Google-service ANRs. It was replaced by the direct filesystem layout with
uncompressed APKs. Historical logs in `build/lite/` include these discarded
prototypes; use the final-run evidence listed below for the delivered image.

For normal use, allocate 1.5–2 GB and install to a fresh virtual disk. Live mode
uses RAM for `/data` and loses photos/account state on reboot.

## Final-run evidence

- `build/lite/delivered-regression.txt`: automatic VirtWifi, DHCP address
  10.0.2.15, DNS and three successful internet pings; Magisk, Pixel identity,
  low-RAM settings, cache-aware memory policy, absent optional packages, and the
  installed Photos APK SHA-256 matching the pinned download.
- `build/lite/delivered-gallery.png` and `delivered-gallery-memory.txt`: local
  JPEG in Photos; **74,072 KiB PSS (72.3 MiB)** for Photos and **206,896 KiB
  (202.0 MiB) MemAvailable**, with no swap.
- `build/lite/delivered-launch.txt`: fresh-data first activity launch **6245 ms**;
  initialization of the app continues after the activity draws.
- `build/lite/delivered-viewer.png`: selected local image opened in the viewer.
- `build/lite/delivered-viewer1536.png`: fully rendered local-image viewer at
  1536 MB, after the sign-in-page check.
- `build/lite/delivered-signin1536.png` and `delivered-signin1536.txt`: the
  delivered ISO reached Google's **Email or phone** sign-in form from Photos
  at **1536 MB RAM**, without Play Store. No credentials were entered. The host
  saved/suspended the test VM during this check; resuming it preserved the form.
- `build/lite/photos-signature.txt`: verified Google signer SHA-256
  `3d7a1223019aa39d9ea0e3436ab7c0896bfb4fb679f4de5fe7c23f326c8f994a`.
- `build/lite/final-vm-config.txt`: tested VirtualBox configuration.

The delivered ISO is **1,204,748,288 bytes**. SHA-256:
`ae79c812920b05ae71586a2272fc8301909a627cc7988c32e94de42d6040b5e2`.
The checksum sidecar passes, and the direct-system SquashFS hash matches the
build manifest. Python and shell syntax checks passed for the modified builders
and startup helpers.
