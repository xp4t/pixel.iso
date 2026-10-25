#!/usr/bin/env python3
"""Create the Photos-only /system image while preserving ext4 metadata/xattrs."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent
WORK = ROOT / 'build/lite'
STOCK = WORK / 'stock/squash/system.img'
IMAGE_DIR = WORK / 'system-root'
IMAGE = IMAGE_DIR / 'system.img'
PHOTOS = ROOT / 'downloads/GooglePhotos-latest.apk'

KEEP_APPS = {
    'GoogleExtShared', 'LatinIME', 'PacProcessor', 'CertInstaller', 'KeyChain',
    'HTMLViewer', 'WebViewGoogle', 'CaptivePortalLogin',
}
KEEP_PRIV = {
    'GoogleLoginService', 'ExternalStorageProvider', 'MtpDocumentsProvider',
    'VpnDialogs', 'StatementService', 'FusedLocation', 'InputDevices',
    'TelephonyProvider', 'Shell', 'DocumentsUI', 'SystemUI', 'SettingsIntelligence',
    'GmsCore', 'GoogleOneTimeInitializer', 'Settings', 'ProxyHandler',
    'GoogleExtServices', 'UserDictionaryProvider', 'DownloadProvider',
    'StorageManager', 'TeleService', 'ContactsProvider', 'DefaultContainerService',
    'SettingsProvider', 'MediaProvider', 'Launcher3QuickStep',
    'GoogleServicesFramework', 'GooglePackageInstaller',
}

PROPERTIES = {
    'ro.config.low_ram': 'true',
    'ro.setupwizard.mode': 'DISABLED',
    'ro.product.cpu.abilist': 'x86_64',
    'ro.product.cpu.abilist32': '',
    'ro.product.cpu.abilist64': 'x86_64',
    'ro.enable.native.bridge.exec': '0',
    'ro.enable.native.bridge.exec64': '0',
    'ro.dalvik.vm.native.bridge': '0',
    'dalvik.vm.heapstartsize': '8m',
    'dalvik.vm.heapgrowthlimit': '192m',
    'dalvik.vm.heapsize': '256m',
    'dalvik.vm.heapmaxfree': '4m',
    'dalvik.vm.dex2oat-Xmx': '128m',
    'ro.zygote': 'zygote64',
    'debug.sf.nobootanimation': '1',
    'ro.sf.lcd_density': '160',
}

def run(*args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)

def debug(command):
    return run('debugfs', '-R', command, STOCK, stdout=subprocess.PIPE,
               stderr=subprocess.DEVNULL).stdout.decode()

def entries(path):
    result = []
    for line in debug(f'ls -p {path}').splitlines():
        fields = line.split('/')
        if len(fields) >= 7 and fields[1].isdigit() and fields[5] not in ('.', '..'):
            result.append((fields[5], int(fields[2], 8), int(fields[6] or 0)))
    return result

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while chunk:=f.read(1024*1024): h.update(chunk)
    return h.hexdigest()

def main():
    assert STOCK.is_file() and PHOTOS.is_file(), 'Extract the base /system and download Photos first'
    certificate=run('apksigner','verify','--print-certs',PHOTOS,stdout=subprocess.PIPE).stdout.decode()
    expected='3d7a1223019aa39d9ea0e3436ab7c0896bfb4fb679f4de5fe7c23f326c8f994a'
    assert f'Signer #1 certificate SHA-256 digest: {expected}' in certificate, 'Unexpected Photos signer'
    badging=run('aapt','dump','badging',PHOTOS,stdout=subprocess.PIPE).stdout.decode()
    assert "name='com.google.android.apps.photos'" in badging
    assert "'x86_64'" in badging and int(re.search(r"sdkVersion:'(\d+)'",badging)[1])<=28
    photos_version=re.search(r"versionName='([^']+)'",badging)[1]
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    run('cp', '--reflink=auto', '--sparse=always', STOCK, IMAGE)
    commands=[]
    removed=[]
    def remove(path):
        for name, mode, size in entries(path):
            child=path.rstrip('/')+'/'+name
            if mode & 0o170000 == 0o040000:
                remove(child)
            else:
                commands.append(f'rm {child}')
                removed.append({'path':child,'bytes':size})
        commands.append(f'rmdir {path}')

    for base, keep in [('/app',KEEP_APPS),('/priv-app',KEEP_PRIV)]:
        for name,mode,size in entries(base):
            if name not in keep: remove(base+'/'+name)
    # This variant targets VMs: virtual NICs need no physical Wi-Fi/GPU firmware.
    for name,mode,size in entries('/lib/firmware'):
        if name in {'regulatory.db','regulatory.db.p7s','regulatory.bin'}: continue
        path='/lib/firmware/'+name
        if mode & 0o170000 == 0o040000: remove(path)
        else:
            commands.append(f'rm {path}')
            removed.append({'path':path,'bytes':size})

    context=WORK/'system-file-context'
    context.write_bytes(b'u:object_r:system_file:s0\0')
    def label(path):
        commands.append(f'ea_set -f {context} {path} security.selinux')
    def mkdir(path):
        commands.extend([f'mkdir {path}', f'set_inode_field {path} mode 040755'])
        label(path)
    def write(source,dest):
        commands.extend([f'write {source} {dest}',f'set_inode_field {dest} mode 0100644'])
        label(dest)

    mkdir('/app/Photos')
    write(PHOTOS,'/app/Photos/Photos.apk')
    mkdir('/app/Photos/lib')
    mkdir('/app/Photos/lib/x86_64')
    native=WORK/'photos-native'
    native.mkdir(exist_ok=True)
    with zipfile.ZipFile(PHOTOS) as z:
        for member in z.infolist():
            if member.filename.startswith('lib/x86_64/') and not member.is_dir():
                name=Path(member.filename).name
                assert re.fullmatch(r'[A-Za-z0-9_.+-]+',name)
                local=native/name
                local.write_bytes(z.read(member))
                write(local,'/app/Photos/lib/x86_64/'+name)

    props=debug('cat /build.prop')
    lines=[]
    seen=set()
    for line in props.splitlines():
        key=line.partition('=')[0]
        if key in PROPERTIES:
            if key not in seen: lines.append(key+'='+PROPERTIES[key]); seen.add(key)
        else: lines.append(line)
    lines.extend(key+'='+value for key,value in PROPERTIES.items() if key not in seen)
    propfile=WORK/'lite-build.prop'
    propfile.write_text('\n'.join(lines)+'\n')
    commands.append('rm /build.prop')
    write(propfile,'/build.prop')
    commandfile=WORK/'system-debugfs.commands'
    commandfile.write_text('\n'.join(commands)+'\n')
    proc=run('debugfs','-w','-f',commandfile,IMAGE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (WORK/'system-edit.log').write_bytes(proc.stdout+proc.stderr)
    for marker in [b'Could not allocate',b'File not found',b'Usage:',b'write:']:
        assert marker not in proc.stderr, proc.stderr[-3000:].decode(errors='replace')
    check=subprocess.run(['e2fsck','-fy',str(IMAGE)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (WORK/'fsck.log').write_bytes(check.stdout)
    assert check.returncode in (0,1),check.stdout.decode()
    run('resize2fs','-M',IMAGE)
    run('zerofree',IMAGE)
    report={
        'kept_app_directories':sorted(KEEP_APPS|{'Photos'}),
        'kept_priv_app_directories':sorted(KEEP_PRIV),
        'removed_files':removed,'removed_uncompressed_bytes':sum(x['bytes'] for x in removed),
        'photos':{'version':photos_version,'sha256':sha(PHOTOS),
                  'signer_sha256':'3d7a1223019aa39d9ea0e3436ab7c0896bfb4fb679f4de5fe7c23f326c8f994a',
                  'native_abi':'x86_64'},
        'filesystem_layout':'prepared_ext4',
        'properties':PROPERTIES,
    }
    (WORK/'system-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Lite /system prepared. Run pack_lite_system.sh to create direct SquashFS.',flush=True)

if __name__=='__main__': main()
