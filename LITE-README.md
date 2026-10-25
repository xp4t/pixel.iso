# pixel.iso Photos Lite — technical guide

New to virtual machines? Start with the [beginner guide](README.md#get-started).
The ISO's boot menu retains the name **Pixel Photos Lite**.

`androidiso-lite.iso` is the lightweight **Intel/AMD x86-64 VM** variant of this
Android-x86 9.0-r2 remaster. The original `androidiso.iso` is still available.

Google Photos **7.98.0.1001971222** is preinstalled, including its native x86-64
libraries. Its APK retains Google's signature and has not been modified or
re-signed. The build verifies the signer, package name, Android compatibility and
native architecture before including it. Version and hashes are recorded in
`BUILD-MANIFEST-lite.json`.

Play Store, Chrome, Google Search, Gmail, Calendar, the separate gallery, camera,
music player, Taskbar, printing and other bundled extras are removed. Google
account sign-in, Play services, Services Framework, WebView, keyboard, file/media
providers, Settings and Android's core services remain. Magisk 26.4 and the custom
Pixel/sailfish identity module remain; LSPosed is omitted and Zygisk is disabled
to reduce background work. The full ISO retains LSPosed.

The system uses Android's low-RAM mode, a single 64-bit app runtime, a simple
Launcher3 home screen, disabled animations and a smaller cached-process limit.
The default BIOS live preset is 800×600 with a 32-bit framebuffer. A direct
SquashFS system removes the extra nested filesystem layer used by the base ISO.
Physical Wi-Fi/GPU firmware is removed: this variant targets virtual hardware.

About 648 MiB of original uncompressed files were removed before adding Photos
and its native libraries. App APKs stay uncompressed in the outer SquashFS to
avoid repeated decompression during memory pressure. This makes the ISO about
**1.12 GiB**, larger than the full image; the tradeoff improves runtime behavior
on the small VM. The main aim is less background activity and lower memory use.

## Run it

1. Create a fresh **Other Linux (64-bit)** VM with long mode, PAE and hardware
   virtualization enabled. Use **2 CPUs**, BIOS firmware, VBoxVGA/standard VGA
   and 3D acceleration off. In VirtualBox, 32 MB video RAM was tested.
2. Allocate **1.5–2 GB RAM** for account setup and normal use. Basic local Photos
   viewing was tested with 1 GB, but large libraries and editing need more memory.
   Photos memory measurements are recorded in `LITE-TEST-RESULTS.md`; these are
   snapshots, not fixed limits or a guarantee of lag-free operation.
3. Attach `androidiso-lite.iso` and use its default software-graphics live entry.
   Enable Adapter 1, **NAT**, and **Cable connected**. Android automatically uses
   **VirtWifi**, which shares the host connection; it does not list the host's
   physical Wi-Fi networks. PCnet-FAST III was tested.
4. For persistent photos and sign-in, use a fresh **16 GB or larger virtual disk**
   and the installation entry. Select only that new VM disk, create a bootable
   partition, format ext4, and install GRUB. Detach the ISO before booting from it.
   The installer retains a safe 1024×768, 32-bit BIOS graphics preset.

**Live mode stores data in RAM and clears it on reboot**, including account state
and copied photos. Use a fresh data partition for Lite: older full-image user
data may retain apps and modules that this variant removes.

Photos is Google's normal app. Optional editing downloads and large cloud
libraries can increase its memory/storage use. Keeping the signed app intact
preserves its update and account compatibility. Pixel identity is a cosmetic
device-property module; Google certification or service benefits are not
guaranteed. The underlying OS remains Android 9.

See `LITE-TEST-RESULTS.md` for measured results and the limits of verification.
The delivered image reached Google's email/phone sign-in page at 1.5 GB without
Play Store; completed account authentication and cloud backup remain untested.

## Verify and rebuild

```sh
sha256sum -c androidiso-lite.iso.sha256
```

The supplied `downloads/` directory contains the pinned base ISO, Magisk, LSPosed
asset used by the shared builder, and signed Photos APK. Keep those exact assets
for this build. Rebuild with Docker:

```sh
docker build -t pixeliso-tools:photos-lite -f Dockerfile.lite-build .
mkdir -p build/lite/stock/squash
docker run --rm -v "$PWD:/work" pixeliso-tools:photos-lite \
  xorriso -osirrox on -indev downloads/android-x86_64-9.0-r2.iso \
  -extract /system.sfs build/lite/stock/system.sfs
docker run --rm -v "$PWD:/work" pixeliso-tools:photos-lite \
  unsquashfs -f -d build/lite/stock/squash build/lite/stock/system.sfs
docker run --rm -v "$PWD:/work" pixeliso-tools:photos-lite \
  python3 build_lite_system.py
bash pack_lite_system.sh
docker run --rm -v "$PWD:/work" pixeliso-tools:photos-lite \
  python3 build_iso.py --lite
sha256sum -c androidiso-lite.iso.sha256
```

Packing uses a temporary privileged container with networking disabled to mount
the prepared local ext4 image read-only and preserve filesystem metadata. The
scripts and `profiles/photos-lite/` record the changes. Original component
licenses and provenance are listed in `README.md` and the build manifest.
