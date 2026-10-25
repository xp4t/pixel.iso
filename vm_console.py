#!/usr/bin/env python3
"""Local build diagnostic client, executed inside the tools container."""
import argparse
from pathlib import Path
import select
import socket
import time

p = argparse.ArgumentParser()
p.add_argument('command', nargs='?', default='')
p.add_argument('--seconds', type=float, default=5)
p.add_argument('--socket', default='/work/build/serial.sock')
args = p.parse_args()
s = socket.socket(socket.AF_UNIX)
s.connect(args.socket)
if args.command:
    s.sendall((args.command + '\n').encode())
deadline = time.monotonic() + args.seconds
with Path('/work/build/vm-serial.log').open('ab') as log:
    while time.monotonic() < deadline:
        if select.select([s], [], [], min(1, max(0, deadline-time.monotonic())))[0]:
            data = s.recv(65536)
            if not data:
                break
            log.write(data)
            log.flush()
            print(data.decode(errors='replace'), end='', flush=True)
