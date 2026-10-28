#!/usr/bin/env python3
"""Build androidiso.iso using a stock Android-x86 ISO and pinned release assets.

Run in the supplied tools container: python3 /work/build_iso.py
"""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--lite', action='store_true', help='Build the Photos-only low-RAM variant')
ARGS = parser.parse_args()
LITE = ARGS.lite

ROOT = Path(__file__).resolve().parent
BASE = ROOT / 'downloads/android-x86_64-9.0-r2.iso'
MAGISK = ROOT / 'downloads/Magisk-v26.4.apk'
LSPOSED = ROOT / 'downloads/LSPosed-v1.9.2-7024-zygisk-release.zip'
WORK = ROOT / ('build/repack-lite' if LITE else 'build/repack')

def run(*args, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=True, **kwargs)

def digest(path, algorithm='sha256'):
    h = hashlib.new(algorithm)
    with path.open('rb') as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def put(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)

assert digest(BASE, 'sha1') == '1cc85b5ed7c830ff71aecf8405c7281a9c995aa0', 'Base checksum mismatch'
if WORK.exists():
    shutil.rmtree(WORK)
WORK.mkdir(parents=True)
stock = WORK / 'stock'
stock.mkdir()
for name in ['initrd.img', 'install.img', 'isolinux/isolinux.cfg', 'efi/boot/android.cfg', 'kernel', 'ramdisk.img']:
    target = stock / name
    target.parent.mkdir(parents=True, exist_ok=True)
    run('xorriso', '-osirrox', 'on', '-indev', BASE, '-extract', '/' + name, target)

initrd = WORK / 'initrd'
initrd.mkdir()
run('cpio', '-id', '--no-absolute-filenames', cwd=initrd,
    input=gzip.decompress((stock / 'initrd.img').read_bytes()))
payload = initrd / 'pixeliso'
payload.mkdir()
with zipfile.ZipFile(MAGISK) as z:
    for abi, names in [('x86_64', ['busybox', 'magisk64', 'magiskinit', 'magiskpolicy', 'magiskboot']),
                       ('x86', ['magisk32'])]:
        for name in names:
            put(payload / name, z.read(f'lib/{abi}/lib{name}.so'), 0o755)
    for name in z.namelist():
        if name.startswith('assets/') and not name.endswith('/'):
            put(payload / name, z.read(name))
shutil.copyfile(MAGISK, payload / 'magisk.apk')
for source in (ROOT / 'payload').iterdir():
    if source.name != '99_pixeliso.sh':
        shutil.copyfile(source, payload / source.name)
        (payload / source.name).chmod(0o755 if source.suffix == '.sh' else 0o644)
if LITE:
    for source in (ROOT / 'profiles/photos-lite').iterdir():
        shutil.copyfile(source, payload / source.name)
        (payload / source.name).chmod(0o755 if source.suffix == '.sh' else 0o644)
shutil.copyfile(ROOT / 'payload/99_pixeliso.sh', initrd / 'scripts/99_pixeliso')
mount_script = initrd / 'scripts/2-mount'
text = mount_script.read_text()
assert 'device_mount_data || mount -t tmpfs tmpfs data' in text
mount_script.write_text(text.replace('device_mount_data || mount -t tmpfs tmpfs data',
                                    'device_mount_data || pixeliso_mount_live_data'))

modules = payload / 'modules'
modules.mkdir()
shutil.copytree(ROOT / 'modules/pixelify_vm', modules / 'pixelify_vm')
lsp = modules / 'zygisk_lsposed'
with zipfile.ZipFile(LSPOSED) as z:
    # Exactly the installed layout used by customize.sh for x64 / Android 9.
    for name in ['module.prop', 'post-fs-data.sh', 'service.sh', 'uninstall.sh',
                 'sepolicy.rule', 'framework/lspd.dex', 'daemon.apk', 'daemon',
                 'manager.apk', 'system.prop', 'README.md']:
        put(lsp / name, z.read(name), 0o744 if name == 'daemon' else 0o644)
    for abi in ['x86', 'x86_64']:
        put(lsp / f'zygisk/{abi}.so', z.read(f'lib/{abi}/liblspd.so'))
if LITE:
    shutil.rmtree(lsp)

filelist = b''.join(str(p.relative_to(initrd)).encode() + b'\0'
                    for p in sorted(initrd.rglob('*')))
archive = run('cpio', '--null', '-o', '-H', 'newc', '--owner=0:0',
              cwd=initrd, input=filelist, stdout=subprocess.PIPE).stdout
patched = WORK / 'initrd.img'
with patched.open('wb') as f:
    with gzip.GzipFile(fileobj=f, mode='wb', mtime=0) as gz:
        gz.write(archive)

# The stock installer strips the boot-time vga argument and uses a 16-bit VESA
# fallback. Keep the tested 32-bit framebuffer for installed guests as well.
installer = WORK / 'installer'
installer.mkdir()
run('cpio', '-id', '--no-absolute-filenames', cwd=installer,
    input=gzip.decompress((stock / 'install.img').read_bytes()))
install_script = installer / 'scripts/1-install'
text = install_script.read_text().replace('vga=788 modeset=0', 'vga=0x344 modeset=0')
lines = text.splitlines()
index = next(i for i, line in enumerate(lines) if line.startswith('\tcmdline=`sed '))
lines.insert(index + 1, '\tcmdline="$cmdline vga=0x344"')
install_script.write_text('\n'.join(lines) + '\n')
filelist = b''.join(str(p.relative_to(installer)).encode() + b'\0'
                    for p in sorted(installer.rglob('*')))
archive = run('cpio', '--null', '-o', '-H', 'newc', '--owner=0:0',
              cwd=installer, input=filelist, stdout=subprocess.PIPE).stdout
patched_install = WORK / 'install.img'
with patched_install.open('wb') as f:
    with gzip.GzipFile(fileobj=f, mode='wb', mtime=0) as gz:
        gz.write(archive)

patched_ramdisk = None
if LITE:
    # A single native 64-bit zygote avoids the unused 32-bit runtime process.
    ramdisk = WORK / 'ramdisk'
    ramdisk.mkdir()
    run('cpio', '-id', '--no-absolute-filenames', cwd=ramdisk,
        input=gzip.decompress((stock / 'ramdisk.img').read_bytes()))
    zygote = (ramdisk / 'init.zygote64_32.rc').read_text().split('service zygote_secondary')[0]
    (ramdisk / 'init.zygote64.rc').write_text(zygote)
    init_rc = ramdisk / 'init.rc'
    init_rc.write_text('\n'.join(line for line in init_rc.read_text().splitlines()
                                 if 'start zygote_secondary' not in line)+'\n')
    defaults = ramdisk / 'default.prop'
    replacements = {
        'ro.zygote': 'zygote64', 'ro.config.low_ram': 'true',
        # This kernel lacks MEMCG_SWAP. Pie's pressure-only lmkd path otherwise
        # kills Google services even with reclaimable file cache available.
        'ro.lmk.use_minfree_levels': 'true',
        'ro.dalvik.vm.native.bridge': '0', 'dalvik.vm.dex2oat-Xmx': '128m',
        'ro.product.cpu.abilist': 'x86_64', 'ro.product.cpu.abilist32': '',
        'ro.product.cpu.abilist64': 'x86_64', 'ro.setupwizard.mode': 'DISABLED',
        'debug.sf.nobootanimation': '1', 'ro.sf.lcd_density': '160',
    }
    default_lines = [line for line in defaults.read_text().splitlines()
                     if line.partition('=')[0] not in replacements]
    default_lines += [key+'='+value for key,value in replacements.items()]
    defaults.write_text('\n'.join(default_lines)+'\n')
    filelist = b''.join(str(p.relative_to(ramdisk)).encode()+b'\0' for p in sorted(ramdisk.rglob('*')))
    archive = run('cpio', '--null', '-o', '-H', 'newc', '--owner=0:0', cwd=ramdisk,
                  input=filelist, stdout=subprocess.PIPE).stdout
    patched_ramdisk = WORK / 'ramdisk.img'
    with patched_ramdisk.open('wb') as f:
        with gzip.GzipFile(fileobj=f, mode='wb', mtime=0) as gz: gz.write(archive)

# Default to software rendering for broad VM compatibility. Keep an accelerated
# option and the normal installer available in the existing BIOS/EFI menus.
cfg = WORK / 'isolinux.cfg'
cfg.write_text('''default vesamenu.c32
prompt 0
timeout 100
menu title Pixel Android VM - Android 9 x86_64
menu background android-x86.png

label pixelvm
  menu label Pixel Android VM - Live (software graphics)
  menu default
  kernel /kernel
  append initrd=/initrd.img root=/dev/ram0 androidboot.selinux=permissive androidboot.hardware=android_x86_64 quiet nomodeset xforcevesa HWACCEL=0 vga=0x344 SRC= DATA=

label accelerated
  menu label Pixel Android VM - Live (accelerated graphics)
  kernel /kernel
  append initrd=/initrd.img root=/dev/ram0 androidboot.selinux=permissive androidboot.hardware=android_x86_64 quiet SRC= DATA=

label install
  menu label Install Pixel Android VM to virtual hard disk
  kernel /kernel
  append initrd=/initrd.img root=/dev/ram0 androidboot.selinux=permissive androidboot.hardware=android_x86_64 INSTALL=1 nomodeset xforcevesa HWACCEL=0 vga=0x344 SRC=

label debug
  menu label Pixel Android VM - Debug console
  kernel /kernel
  append initrd=/initrd.img root=/dev/ram0 androidboot.selinux=permissive androidboot.hardware=android_x86_64 DEBUG=2 nomodeset xforcevesa HWACCEL=0 vga=0x344 SRC= DATA=
''')
efi = WORK / 'android.cfg'
efi.write_text('''set default=0
set timeout=10
menuentry 'Pixel Android VM - Live (software graphics)' {
    search --no-floppy --file --set=root /initrd.img
    linux /kernel root=/dev/ram0 androidboot.selinux=permissive androidboot.hardware=android_x86_64 quiet nomodeset xforcevesa HWACCEL=0 SRC= DATA=
    initrd /initrd.img
}
menuentry 'Pixel Android VM - Live (accelerated graphics)' {
    search --no-floppy --file --set=root /initrd.img
    linux /kernel root=/dev/ram0 androidboot.selinux=permissive androidboot.hardware=android_x86_64 quiet SRC= DATA=
    initrd /initrd.img
}
menuentry 'Install Pixel Android VM to virtual hard disk' {
    search --no-floppy --file --set=root /initrd.img
    linux /kernel root=/dev/ram0 androidboot.selinux=permissive androidboot.hardware=android_x86_64 INSTALL=1 nomodeset xforcevesa HWACCEL=0 SRC=
    initrd /initrd.img
}
''')
if LITE:
    cfg.write_text(cfg.read_text().replace('Pixel Android VM','Pixel Photos Lite')
                   .replace('vga=0x344','vga=0x343'))
    efi.write_text(efi.read_text().replace('Pixel Android VM','Pixel Photos Lite'))
    # The base installer image retains 32-bit 1024x768 as a safe installed fallback.

manifest = {
    'base': {'version': 'Android-x86 9.0-r2 x86_64', 'sha1': digest(BASE, 'sha1'),
             'sha256': digest(BASE), 'publisher': 'https://www.android-x86.org/releases/releasenote-9-0-r2.html'},
    'magisk': {'version': '26.4', 'sha256': digest(MAGISK), 'source': 'https://github.com/topjohnwu/Magisk/releases/tag/v26.4'},
    'lsposed': {'version': '1.9.2 (7024), Zygisk', 'sha256': digest(LSPOSED), 'source': 'https://github.com/LSPosed/LSPosed/releases/tag/v1.9.2'},
    'pixelify': {'version': 'Pixelify-VM 1.0 (custom)', 'device': 'Pixel / sailfish',
                 'note': 'Not upstream Kingsman44 Pixelify; identity-only VM-compatible replacement.'},
    'network': {'version': 1, 'profile': 'VirtWifi', 'addressing': 'DHCP',
                'scope': 'Fresh data with the Android-x86 virt_wifi driver; existing Wi-Fi stores are preserved.',
                'profile_sha256': digest(ROOT / 'payload/virtwifi-config.xml'),
                'helper_sha256': digest(ROOT / 'payload/connect-virtwifi.sh')},
    'app_recovery': {
        'setup_permissions_sha256': digest(ROOT / 'payload/setup-permissions.sh'),
        'playstore_recovery_sha256': digest(ROOT / 'payload/playstore-recovery.sh'),
        'playstore_scope': 'Cache-only recovery for GridClusterPaddingView ClassCastException, once per boot',
    },
}
if LITE:
    manifest['variant'] = 'Photos Lite x86_64'
    manifest['lsposed'] = {'included': False, 'zygisk_enabled': False}
    manifest['lite_system'] = json.loads((ROOT / 'build/lite/system-manifest.json').read_text())
    manifest['lite_ramdisk_properties'] = replacements
manifest_path = ROOT / ('BUILD-MANIFEST-lite.json' if LITE else 'BUILD-MANIFEST.json')
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
output = ROOT / ('androidiso-lite.iso' if LITE else 'androidiso.iso')
if output.exists():
    output.unlink()
extra_maps=[]
if LITE:
    extra_maps = ['-map', ROOT / 'build/lite/system.sfs', '/system.sfs',
                  '-map', patched_ramdisk, '/ramdisk.img',
                  '-map', ROOT / 'profiles/photos-lite', '/pixeliso-source/photos-lite']
run('xorriso', '-indev', BASE, '-outdev', output,
    *extra_maps,
    '-map', patched, '/initrd.img',
    '-map', patched_install, '/install.img',
    '-map', cfg, '/isolinux/isolinux.cfg',
    '-map', efi, '/efi/boot/android.cfg',
    '-map', manifest_path, '/BUILD-MANIFEST.json',
    '-map', ROOT / 'modules/pixelify_vm', '/pixeliso-source/pixelify_vm',
    '-map', ROOT / 'payload', '/pixeliso-source/payload',
    '-volid', 'PIXEL_PHOTOS_LITE' if LITE else 'PIXEL_ANDROID_VM', '-boot_image', 'any', 'replay', '-commit')
(ROOT / (output.name+'.sha256')).write_text(f'{digest(output)}  {output.name}\n')
print(f'Created {output}: {output.stat().st_size:,} bytes', flush=True)
