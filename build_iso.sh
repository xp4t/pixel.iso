#!/usr/bin/env bash
# Build the Full x86-64 live/install ISO, including the repository's repairs.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$ROOT"

usage() {
  cat <<'EOF'
Usage: ./build_iso.sh [options]

  --install-deps       Install native tools with apt (Debian/Ubuntu; uses sudo)
  --docker             Build with the supplied Dockerfile instead of host tools
  --offline            Require verified local downloads; do not download/build images
  --download-only      Fetch and verify inputs without building the ISO
  --configure-vm NAME  Apply tested settings and attach ISO to an existing,
                       powered-off VirtualBox VM (IDE optical drive required)
  -h, --help           Show this help

Default: download missing pinned assets, build androidiso.iso, verify its checksum.
Produces the Full edition. Photos Lite has a separate workflow in LITE-README.md.
See BUILDING.md for requirements, download links and installation instructions.
EOF
}
die() { echo "Error: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "Missing $1. See BUILDING.md or use --install-deps / --docker."; }
install_deps=0 docker_build=0 offline=0 download_only=0 vm=''
while (($#)); do
  case "$1" in
    --install-deps) install_deps=1 ;;
    --docker) docker_build=1 ;;
    --offline) offline=1 ;;
    --download-only) download_only=1 ;;
    --configure-vm)
      (($# >= 2)) && [[ -n "$2" && "$2" != --* ]] || die '--configure-vm requires a VM name'
      vm=$2; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
  shift
done
(( !install_deps || (!offline && !docker_build) )) || die '--install-deps cannot be combined with --offline or --docker'
[[ -z "$vm" || "$download_only" == 0 ]] || die '--configure-vm requires an ISO build'
if ((install_deps)); then
  need apt-get
  elevate=()
  if ((EUID != 0)); then need sudo; elevate=(sudo); fi
  "${elevate[@]}" apt-get update
  "${elevate[@]}" apt-get install -y python3 curl ca-certificates cpio xorriso coreutils
fi
for tool in python3 sha1sum sha256sum; do need "$tool"; done
((offline)) || need curl
if ((!download_only)); then
  if ((docker_build)); then
    need docker
    docker info >/dev/null 2>&1 || die 'Docker daemon is unavailable or access is denied'
  else
    need cpio; need xorriso
  fi
fi
if [[ -n "$vm" ]]; then
  need VBoxManage
  info="$(VBoxManage showvminfo "$vm" --machinereadable)"
  [[ "$info" == *'VMState="poweroff"'* ]] || die "VM '$vm' must be fully powered off (not saved or running)"
  [[ "$info" == *'storagecontrollername0="IDE"'* || "$info" == *'="IDE"'* ]] || die "VM '$vm' needs a storage controller named IDE"
  [[ "$info" == *'"IDE-1-0"="none"'* || "$info" == *'"IDE-1-0"='*'.iso"'* ]] || die 'IDE port 1 device 0 must be an empty optical drive or mounted ISO'
fi
mkdir -p downloads build
mkdir build/iso-builder.lock 2>/dev/null || die 'Another build is active (if interrupted, remove build/iso-builder.lock)'
trap 'rmdir "$ROOT/build/iso-builder.lock"' EXIT

# Reject corrupt existing inputs instead of silently trusting a nonempty file.
fetch() {
  local name=$1 algorithm=$2 expected=$3
  shift 3
  local target="$ROOT/downloads/$name" url
  if [[ -f "$target" ]]; then
    printf '%s  %s\n' "$expected" "$target" | "${algorithm}sum" --check --status || die "Checksum mismatch: $target. Move it aside and retry."
    echo "Verified $name"
    return
  fi
  (( !offline )) || die "Offline input missing: $target"
  for url in "$@"; do
    echo "Downloading $name from $url"
    if curl --fail --location --show-error --retry 3 --connect-timeout 30 \
        --output "$target.part" "$url" &&
        printf '%s  %s\n' "$expected" "$target.part" | "${algorithm}sum" --check --status; then
      mv -- "$target.part" "$target"
      return
    fi
    echo "Download or checksum failed; trying the next source." >&2
    rm -f -- "$target.part"
  done
  die "Could not fetch $name. Download it manually using BUILDING.md and rerun."
}
fetch android-x86_64-9.0-r2.iso sha1 1cc85b5ed7c830ff71aecf8405c7281a9c995aa0 \
  'https://sourceforge.net/projects/android-x86/files/Release%209.0/android-x86_64-9.0-r2.iso/download' \
  'https://archive.org/download/android-x86_64-9.0-r2/android-x86_64-9.0-r2.iso'
fetch Magisk-v26.4.apk sha256 543a96fe26c012d99baf3a3aa5a97b80508d67cc641af7c12ce9f7b226b2b889 \
  'https://github.com/topjohnwu/Magisk/releases/download/v26.4/Magisk-v26.4.apk'
fetch LSPosed-v1.9.2-7024-zygisk-release.zip sha256 0ebc6bcb465d1c4b44b7220ab5f0252e6b4eb7fe43da74650476d2798bb29622 \
  'https://github.com/LSPosed/LSPosed/releases/download/v1.9.2/LSPosed-v1.9.2-7024-zygisk-release.zip'
if ((download_only)); then echo 'All build inputs verified.'; exit 0; fi

if ((docker_build)); then
  image=pixeliso-tools:full
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    (( !offline )) || die "Offline Docker image missing: $image. Run once with --docker online."
    docker build -t "$image" -f Dockerfile.lite-build .
  fi
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -v "$ROOT:/work" "$image" python3 /work/build_iso.py
else
  python3 build_iso.py
fi
sha256sum --check androidiso.iso.sha256

if [[ -n "$vm" ]]; then
  # No disk is created, formatted or partitioned by this script.
  VBoxManage modifyvm "$vm" --ostype Linux_64 --longmode on --pae on \
    --hwvirtex on --ioapic on --cpus 2 --memory 2048 --vram 128 --firmware bios \
    --graphicscontroller vboxvga --accelerate-3d off --nic1 nat \
    --nictype1 Am79C973 --cableconnected1 on --boot1 dvd --boot2 disk --boot3 none --boot4 none
  VBoxManage storageattach "$vm" --storagectl IDE --port 1 --device 0 \
    --type dvddrive --medium "$ROOT/androidiso.iso"
  echo "Configured '$vm'. Start it and choose the live or install boot entry."
fi
printf '\nBuilt: %s/androidiso.iso\nChecksum: %s/androidiso.iso.sha256\n' "$ROOT" "$ROOT"
echo 'For persistent use, install onto a dedicated virtual disk. See BUILDING.md.'
