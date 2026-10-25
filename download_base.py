#!/usr/bin/env python3
"""Fetch the archived, publisher-checksummed Android-x86 release in ranges."""
import concurrent.futures
import hashlib
from pathlib import Path
import subprocess

URL = 'https://archive.org/download/android-x86_64-9.0-r2/android-x86_64-9.0-r2.iso'
SIZE = 965738496
SHA1 = '1cc85b5ed7c830ff71aecf8405c7281a9c995aa0'
CHUNK = 16 * 1024 * 1024
parts = Path('downloads/base-parts')
parts.mkdir(parents=True, exist_ok=True)

def fetch(index):
    start = index * CHUNK
    end = min(SIZE, start + CHUNK) - 1
    target = parts / f'{index:03d}'
    if not target.exists() or target.stat().st_size != end - start + 1:
        subprocess.run(['curl', '-fLsS', '--retry', '5', '--max-time', '180',
                        '--range', f'{start}-{end}', URL, '-o', str(target)], check=True)
    if target.stat().st_size != end - start + 1:
        raise RuntimeError(f'Invalid length: {target}')
    print(f'Part {index + 1}/{(SIZE + CHUNK - 1) // CHUNK} ready', flush=True)
    return target

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
    files = list(pool.map(fetch, range((SIZE + CHUNK - 1) // CHUNK)))
out = Path('downloads/android-x86_64-9.0-r2.iso')
digest = hashlib.sha1()
with out.open('wb') as dest:
    for part in files:
        with part.open('rb') as src:
            while data := src.read(1024 * 1024):
                digest.update(data)
                dest.write(data)
if digest.hexdigest() != SHA1:
    raise RuntimeError('Publisher SHA-1 mismatch')
print(f'Verified {out}: {digest.hexdigest()}', flush=True)
