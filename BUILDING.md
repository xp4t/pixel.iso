# Build and install pixel.iso Full

`build_iso.sh` builds the Full Android 9 x86-64 live/install ISO. It includes
Magisk, LSPosed, Pixelify-VM, automatic VirtWifi setup, the Data Transfer Tool
permission repair, and cache recovery for the observed Play Store search crash.
Google Photos can be installed from Play Store. For the separate edition with
Photos preinstalled, see [LITE-README.md](LITE-README.md).

## Build on Linux

Use Bash, Python 3.8 or newer, curl, cpio, xorriso and GNU coreutils. Allow at
least 4 GB of free disk space and about 1 GB of upstream downloads. The native
build does not require root; installing system packages requires sudo.

```sh
git clone https://github.com/xp4t/pixel.iso.git
cd pixel.iso
./build_iso.sh --install-deps
```

`--install-deps` installs the required tools with apt on Debian/Ubuntu. If the
tools are already installed, simply run `./build_iso.sh`.

Alternatively, with Docker installed and accessible to your user:

```sh
./build_iso.sh --docker
```

The Docker build uses `Dockerfile.lite-build` for its tool environment. Building
the Full ISO does not need a privileged container. The build container runs as
your user with networking disabled; downloading inputs and initially building
the tools image require internet access.

Outputs in the repository directory:

- `androidiso.iso` — about 938 MiB, suitable for live boot or installation.
- `androidiso.iso.sha256` — checksum for the generated ISO.
- `BUILD-MANIFEST.json` — component versions, source links and hashes.

The script checks every input against its pinned checksum, then verifies the
output checksum. It refuses corrupt existing inputs; move the named file aside
before retrying. It rebuilds and replaces an existing `androidiso.iso`.

To download inputs separately and rebuild without network access:

```sh
./build_iso.sh --download-only
./build_iso.sh --offline
# Or, after one online Docker build has created the tools image:
./build_iso.sh --docker --offline
```

## Download links

The script downloads these exact files automatically into `downloads/`. For
manual downloads, retain the filenames below. It does not use floating latest
versions.

| File | Direct download | Release information |
|---|---|---|
| `android-x86_64-9.0-r2.iso` | [SourceForge](https://sourceforge.net/projects/android-x86/files/Release%209.0/android-x86_64-9.0-r2.iso/download), [Internet Archive fallback](https://archive.org/download/android-x86_64-9.0-r2/android-x86_64-9.0-r2.iso) | [Android-x86 9.0-r2 and published SHA-1](https://www.android-x86.org/releases/releasenote-9-0-r2.html) |
| `Magisk-v26.4.apk` | [GitHub asset](https://github.com/topjohnwu/Magisk/releases/download/v26.4/Magisk-v26.4.apk) | [Magisk v26.4](https://github.com/topjohnwu/Magisk/releases/tag/v26.4) |
| `LSPosed-v1.9.2-7024-zygisk-release.zip` | [GitHub asset](https://github.com/LSPosed/LSPosed/releases/download/v1.9.2/LSPosed-v1.9.2-7024-zygisk-release.zip) | [LSPosed v1.9.2](https://github.com/LSPosed/LSPosed/releases/tag/v1.9.2) |

The base uses the publisher's SHA-1; Magisk and LSPosed use SHA-256 pins from the
local assets used for this build. All three values are in `build_iso.sh`.
The generated custom ISO is a local output; this guide does not publish or
promise a hosted ISO download.

## Apply VM settings

Create a VirtualBox VM with a new virtual disk of at least 16 GB. Select **Other
Linux (64-bit)** and skip unattended installation. With the VM fully powered
off, the script can apply settings and attach the ISO:

```sh
./build_iso.sh --offline --configure-vm "pixel"
```

Replace `pixel` with your VM name. The VM must have a controller named `IDE`
with an optical drive at port 1, device 0. The script refuses to replace a hard
disk at that location. Add an IDE optical drive in VirtualBox's Storage settings
if needed. It does not create, format or partition virtual disks, or start the VM.

Applied settings: 64-bit guest type, long mode and PAE enabled, hardware
virtualization enabled, 2 CPUs, 2048 MB RAM, BIOS, VBoxVGA, 128 MB video RAM,
3D acceleration off, NAT with PCnet-FAST III and cable connected, DVD before disk
in the boot order. These replace the corresponding settings on the named VM.
The host must support virtualization and have it enabled in firmware. CPU long
mode is a VM setting; the ISO cannot enable it by itself.

## Install Android to the virtual disk

1. Start the VM and choose **Install Pixel Android VM to virtual hard disk**.
2. Select the dedicated new virtual disk. Create a bootable partition if needed,
   select it, format as **ext4**, and install **GRUB** when asked. Formatting
   erases the selected partition. Read-only `/system` is sufficient.
3. Shut down after installation. Detach the ISO from the optical drive and boot
   from the virtual disk.
4. Allow first boot to finish. Android uses **VirtWifi**, sharing the host's
   internet through NAT. Select VirtWifi manually if existing data retains an
   older network configuration.

The live entry stores data in RAM and loses accounts, settings and added apps
at shutdown. Install to disk for persistence. Disk installation remains
unverified in this session; live-mode app and network checks were performed.

The Data Transfer Tool repair waits up to 15 minutes after boot for setup to
install that package, then grants its required settings permission. Play Store
recovery watches for the specific `GridClusterPaddingView` cast failure, clears
only Store caches and reopens it once per boot. This is a workaround for the old
client, not a Play Store or Android security update. Logs are under `/data/adb/`.
