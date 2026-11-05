#!/usr/bin/env python3
"""Dump every MTD partition of a router over SSH and verify each one with MD5."""
import argparse
import hashlib
import os
import re
import subprocess

LEGACY_SSH = ["-o", "KexAlgorithms=+diffie-hellman-group14-sha1",
              "-o", "HostKeyAlgorithms=+ssh-rsa"]


def ssh_cmd(args, remote):
    cmd = ["ssh", "-o", "LogLevel=ERROR"] + LEGACY_SSH + [f"{args.user}@{args.host}", remote]
    if args.password:
        cmd = ["sshpass", "-p", args.password] + cmd
    return cmd


def run(args, remote):
    return subprocess.run(ssh_cmd(args, remote), capture_output=True, text=True).stdout


def local_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="192.168.2.1")
    p.add_argument("--user", default="root")
    p.add_argument("--password", help="uses sshpass; omit to type it or use a key")
    p.add_argument("--out", default="backup_mtd")
    args = p.parse_args()
    os.makedirs(args.out, exist_ok=True)

    proc_mtd = run(args, "cat /proc/mtd")
    with open(os.path.join(args.out, "proc_mtd.txt"), "w") as f:
        f.write(proc_mtd)

    parts = re.findall(r'(mtd\d+):\s+([0-9a-fA-F]+)\s+[0-9a-fA-F]+\s+"([^"]+)"', proc_mtd)
    bad = 0
    for dev, size_hex, name in parts:
        size = int(size_hex, 16)
        path = os.path.join(args.out, f"{dev}_{re.sub(r'[^A-Za-z0-9_.-]', '_', name)}.bin")
        with open(path, "wb") as f:
            subprocess.run(ssh_cmd(args, f"cat /dev/{dev}ro"), stdout=f)
        got = os.path.getsize(path)
        if got != size:
            print(f"{dev} {name}: SIZE MISMATCH ({got} != {size})")
            bad += 1
            continue
        remote = run(args, f"md5sum /dev/{dev}ro").split()[:1]
        ok = remote and remote[0] == local_md5(path)
        bad += not ok
        print(f"{dev} {name}: {'OK' if ok else 'MD5 MISMATCH'}")
    print(f"{len(parts)} partitions, {bad} failed")


if __name__ == "__main__":
    main()
