# Validation

## Network fix: VirtualBox fresh-boot verification

The original live image was reproduced with no IPv4 address or route and
`Network is unreachable`. The PCnet-FAST III NAT adapter and Android-x86
`virt_wifi` driver were present; Wi-Fi was disabled and no network was saved.
Enabling Wi-Fi and selecting the discovered open **VirtWifi** network established
DHCP, DNS and validated internet access. The host's physical Wi-Fi SSID is not
exposed inside the VM.

The ISO was rebuilt with a VM-only initial VirtWifi profile and a first-boot
helper using Android's `/system/bin/svc wifi enable`. A clean boot caught the
BusyBox `svc` name collision; the explicit absolute path is the tested fix.
The helper runs only for the newly seeded profile, does not overwrite existing
saved-network stores, uses DHCP, and records completion so later Wi-Fi on/off
choices are respected.

Verified with no manual Wi-Fi selection on the rebuilt ISO's fresh live data:

- DHCP address `10.0.2.15/24`, gateway `10.0.2.2`, DHCP-provided DNS.
- IP and DNS-name internet pings: 3/3 replies and no loss in each recorded test.
- Android ConnectivityService: `WIFI`, `CONNECTED/CONNECTED`, `VALIDATED`,
  `SSID: "VirtWifi"`, `explicitlySelected=false`.
- Chrome loaded `https://example.com` and reported **Connection is secure**;
  a screenshot and UI hierarchy were captured. No Google account was used.
- Disabling Wi-Fi remained off; re-enabling reconnected and restored DNS pings
  and Android internet validation.
- Magisk root, LSPosed service, Pixel identity, and both manager APKs still passed.
- A second cold boot of the final ISO again connected automatically, obtained
  DHCP, resolved `example.com`, returned 3/3 ping replies, and was `VALIDATED`.

Evidence is in `build/network/`: `baseline-ip.png`, `wpa.png`,
`fixed-auto-connect.png`, `fresh-boot-connectivity.txt`, `https-browser.png`,
`browser.xml`, `reconnect.txt`, `fresh-boot-regression.txt`,
`second-cold-boot.txt`, `final-regression.txt` and `final-connected.png`.
The prior image is retained as `build/network/androidiso-before-network.iso`.
VMware was not installed on this host; these tests use the actual VirtualBox
`pixell` VM. No disk was formatted or installed during this network test.
The temporary ADB port-forward used for diagnostics was removed after testing.

## VirtualBox follow-up: passed

Tested the existing `pixell` VM with VirtualBox **7.2.22r175245**, using the
unchanged `androidiso.iso` through its actual BIOS/DVD boot path.

The reported x86-64/i686 error was reproduced in the original configuration:
guest type **Other/Unknown**, `longmode=off`. The host CPU supports long mode and
VT-x. The VM was powered off at the kernel error and changed to **Other Linux
(64-bit)** (`Linux_64`), `longmode=on`, PAE on, 2 CPUs, 2048 MB RAM and 128 MB
video memory. VBoxVGA, 3D off, BIOS, existing disk and ISO attachment were retained.

VirtualBox logs confirm VT-x, nested paging, guest long mode, and 32/64-bit guest
support. Android reached the interactive graphical welcome screen. A console
check confirmed:

- Magisk daemon version `26.4:MAGISK:R`.
- `su -c id`: `uid=0(root)` and SELinux context `u:r:magisk:s0`.
- Product model/device: `Pixel` / `sailfish`.
- `sys.boot_completed=1` and a running `lspd` process.
- Two `Success` results in the automatic manager installer log.
- Installed APK paths for both `com.topjohnwu.magisk` and `org.lsposed.manager`.

Evidence and before/after configuration are in `build/virtualbox/`, especially
`cpu-error.png`, `runtime-check.png`, `welcome.png`, `pixell-before.txt`,
`pixell-after.txt`, and `VBox-startup.log`. The ISO did not require rebuilding.
The VM was returned to Android's welcome screen in live mode. No disk formatting,
installation, Google sign-in, or account setup was performed.

EFI firmware boot, installation onto the virtual disk, persistence after an
installed-system reboot, and completing account/setup/launcher flows remain untested.

## Earlier QEMU software-emulation test

The base ISO matches Android-x86's published SHA-1. The final image also has a
SHA-256 sidecar (`androidiso.iso.sha256`). Python build scripts and shell payloads
pass syntax checks.

QEMU 7.2 was run with software CPU emulation (TCG), two CPUs, 2 GB guest RAM,
standard VGA and the ISO as its virtual CD. No KVM device is available on this host.

Confirmed during runtime testing:

- The ISO's BIOS boot menu loads from the virtual CD.
- Android 9 starts from the ISO's kernel and patched initrd.
- `magisk -v` returns `26.4:MAGISK:R`.
- `su -c id` returns `uid=0(root)` with `u:r:magisk:s0`.
- `getprop ro.product.model` returns `Pixel`.
- LSPosed's `lspd` process runs. Its Zygisk companion logs version `1.9.2 (7024)`.
- Both 64-bit and 32-bit zygotes run.
- Android signals `sys.boot_completed=1`; the generated status report confirms
  `Android=9 SDK=28`, `Model=Pixel Device=sailfish ABI=x86_64` and
  `key=zygisk|value=1`. First boot took roughly ten minutes under TCG.
- The final software display preset uses a 32-bit framebuffer. Android's boot
  animation renders; the earlier 16-bit framebuffer crashed SwiftShader and was
  replaced in both the ISO menu and installed GRUB configuration.

Runtime logs and screenshots are in `build/`. Runtime tests used explicit serial
diagnostic arguments and disabled the setup wizard; those arguments are absent
from the default ISO menu. The main runtime test loaded the kernel/initrd directly
through QEMU; the BIOS menu was separately tested from the ISO's boot sector.

EFI boot records are structurally retained but an EFI firmware boot has not been
tested. VMware and a complete installation onto a virtual disk have not been
tested here.

### Historical TCG limitations (manager installation now verified in VirtualBox)

The graphical guest reached Android's startup screen and signalled boot completion,
but a responsive launcher session and both installed manager packages were not
verified. Under TCG, the compositor consumed almost all guest CPU and the package
service was intermittently unavailable (`cmd: Can't find service: package`).
The test VM's boot animation was stopped and compositor thread priorities were
reduced for diagnostics; the ISO retains normal animation and scheduling behavior.

The final installer now retries package installation and installs the bundled full
Magisk APK even if Magisk has already installed its downloader stub. A marker is
written only after both installs succeed. This final retry behavior was exercised
in the running test guest, but package installation did not complete reliably in
the available software-emulation environment. The subsequent VirtualBox test
above verified successful automatic installation of both managers.
