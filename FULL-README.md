# pixel.iso Full — technical guide

For the beginner setup guide and edition comparison, start with
[pixel.iso](README.md). The Photos-focused low-RAM build is documented in
[LITE-README.md](LITE-README.md). This Full guide covers LSPosed and the
original bundled apps. Boot menus retain the name **Pixel Android VM**.

Output: `androidiso.iso`, a custom Android-x86 9.0-r2 **x86-64** live/install ISO.

This is a custom remaster. Live boot to Android's graphical welcome screen,
Magisk root, LSPosed, Pixel identity and successful automatic installation of both
manager apps were verified in **VirtualBox 7.2.22**. See `TEST-RESULTS.md` for
evidence and remaining limits. Hardware virtualization is required for this
64-bit VirtualBox guest.

Included:

- Magisk **26.4**, with its manager installed automatically after Android boots.
- Zygisk enabled on first boot.
- LSPosed **1.9.2 / 7024**, with x86 and x86-64 libraries and its manager.
- **Pixelify-VM 1.0**, a custom Magisk identity module reporting the original
  Google Pixel (`Pixel`, `sailfish`, `Google`).
- Automatic **VirtWifi** setup on fresh VM data, using the VM's NAT connection.

Pixelify-VM is **not** Kingsman44's Pixelify. That project's documented hardware
requirement is ARM64. This replacement changes product identity while preserving
the real x86 ABI, kernel hardware selection, Android API, fingerprint, security
patch level and signing keys. It does not include the original module's ARM
applications, Pixel Launcher, wallpapers, Call Screen, or hardware features.
Google device certification, attestation and service benefits are not guaranteed.
This is an Android 9 base with its original upstream security patch level.

## Virtual machine setup

Use an Intel/AMD x86-64 VM in VirtualBox, VMware, or QEMU:

1. Select **Other Linux (64-bit)**, preferably **legacy BIOS**. Secure Boot must
   be off. EFI boot entries are also retained in the ISO.
2. Allocate **2 CPUs**, **2 GB RAM** (tested on this host), and a new
   **16 GB or larger virtual disk**. Use 4 GB guest RAM only if the host has enough
   spare memory. Enable CPU virtualization on the VM host.
3. Use an IDE or SATA CD/DVD device for the ISO; start with a SATA virtual disk.
   Use standard VGA/VBoxVGA and disable 3D acceleration initially. Use NAT networking.
   The BIOS software preset selects a **1024×768, 32-bit framebuffer**; a 16-bit
   framebuffer can crash this Android release's SwiftShader renderer.
4. Attach `androidiso.iso` and boot. The default **Live (software graphics)** entry
   runs from RAM. Its data, installed apps and module settings disappear on reboot.
5. For persistent use, choose **Install Pixel Android VM to virtual hard disk**.
   In the installer, select only the VM's intended virtual disk, create a bootable
   partition, format it as **ext4**, and install GRUB. Read-only `/system` is fine.
6. Detach the ISO and reboot from the virtual disk. Give first boot a few minutes
   for Android initialization and automatic manager installation.
   Software CPU emulation without hardware virtualization can take much longer.

### If the kernel says it detected an i686 CPU

The ISO requires a 64-bit virtual CPU. In the powered-off VM, set the guest OS to
**Other Linux (64-bit)** and enable long mode. The existing `pixell` VM on this
host had `longmode=off`; correcting it fixed this exact error without changing
the ISO. The tested configuration uses 2 CPUs, 2048 MB RAM, 128 MB video RAM,
VBoxVGA, 3D acceleration off, BIOS firmware, and the ISO on the IDE DVD device.

For a powered-off VM named `pixell`, the relevant command is:

```sh
VBoxManage modifyvm pixell --ostype Linux_64 --longmode on --pae on
```

Open Magisk to check root and the enabled LSPosed and Pixelify-VM modules.
Open LSPosed Manager to install and configure the Xposed modules you choose.
No unrelated Xposed modules are included. Disable Pixelify-VM in Magisk and reboot
to restore Android-x86's original product identity. Later boots respect module
disable/removal choices and do not silently reinstall modules.

Root integration is carried in `initrd.img`, which the standard Android-x86
installer copies onto the virtual disk. Live mode uses a sparse temporary ext2
image in RAM for `/data`, allowing Magisk modules to run without formatting a disk.

## Networking

In a VM, Android uses the virtual network named **VirtWifi**. The VM shares the
host's internet connection through its NAT adapter; the guest does not scan for
the host's physical Wi-Fi SSID. Keep Adapter 1 enabled, attached to **NAT**, with
**Cable connected** checked. The existing PCnet-FAST III adapter was verified.

On fresh data, this ISO saves the VirtWifi profile before Android starts its Wi-Fi
service and enables it once after boot. DHCP, DNS, routing and internet validation
are handled by Android. No static IP or replacement DNS server is imposed.
Existing saved-network files are preserved. Later user Wi-Fi on/off choices are
respected. Live mode gets this setup afresh on each boot because its data is in RAM.

For data created by an older ISO, connect to **VirtWifi** once in Android's Wi-Fi
settings; this build deliberately does not overwrite existing saved networks.
Network evidence and regression checks are recorded in `build/network/` and
`TEST-RESULTS.md`.

## Build and provenance

`BUILD-MANIFEST.json` records component versions, upstream links and SHA-256 hashes.
The base ISO is additionally checked against Android-x86's published SHA-1:
`1cc85b5ed7c830ff71aecf8405c7281a9c995aa0`.

The local changes are in `payload/`, `modules/pixelify_vm/`, and `build_iso.py`.
The ISO also includes these payload sources under `/pixeliso-source`.
The base ISO's bootable BIOS/EFI structure is preserved with xorriso's boot replay.

With the pinned assets in `downloads/`, rebuild using Python 3, cpio and xorriso:

```sh
python3 build_iso.py
sha256sum -c androidiso.iso.sha256
```

The build environment used here is the `pixeliso-tools` Debian container:

```sh
docker exec pixeliso-tools python3 /work/build_iso.py
```

If the build container is stopped, run `docker start pixeliso-tools` first.

Sources and licenses:

- Android-x86: https://www.android-x86.org/releases/releasenote-9-0-r2.html
  and https://www.android-x86.org/source.html (components retain their own licenses).
- Magisk 26.4: https://github.com/topjohnwu/Magisk/tree/v26.4 (GPL-3.0).
- LSPosed 1.9.2: https://github.com/LSPosed/LSPosed/tree/v1.9.2 (GPL-3.0).
- Integration reference: https://github.com/KhanhNguyen9872/initrd-magisk (GPL-3.0).
- Original Pixelify requirements: https://github.com/Kingsman44/Pixelify.

Local scripts and the custom Pixelify-VM module are provided under GPL-3.0-or-later.
