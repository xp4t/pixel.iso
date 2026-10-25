#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
# Uses only the prepared local image. Mount it read-only in a private container
# namespace; the host network and the container's root filesystem stay disabled.
docker run --rm --privileged --network none --read-only --tmpfs /mnt \
  -v "$PWD:/work" pixeliso-tools:photos-lite sh -c '
    set -e
    mkdir /mnt/root
    mount -t ext4 -o loop,ro /work/build/lite/system-root/system.img /mnt/root
    trap "umount /mnt/root" EXIT
    mksquashfs /mnt/root /work/build/lite/system-direct.sfs -noappend \
      -comp gzip -Xcompression-level 6 -b 65536 -processors 2 -mem 256M \
      -action "uncompressed@name(*.apk)"
  '
python3 - <<'PY'
import hashlib,json
from pathlib import Path
root=Path('build/lite')
source=root/'system-direct.sfs'
h=hashlib.sha256()
with source.open('rb') as f:
    while chunk:=f.read(1024*1024):h.update(chunk)
manifest=json.loads((root/'system-manifest.json').read_text())
manifest.update(filesystem_layout='direct_squashfs',apk_outer_compression='none',
                system_sfs_bytes=source.stat().st_size,system_sfs_sha256=h.hexdigest())
temporary=root/'system-manifest.new.json'
temporary.write_text(json.dumps(manifest,indent=2)+'\n')
temporary.replace(root/'system-manifest.json')
source.replace(root/'system.sfs')
print('Direct SquashFS ready:',manifest['system_sfs_bytes'],'bytes')
PY
