#!/usr/bin/env python3

import argparse
import platform
import sys
import urllib.request
from pathlib import Path
from typing import cast

if sys.platform == "cygwin":
    sys.exit(
        f"Cygwin/MSYS2 is not supported."
        f"\nPlease use native Windows Python instead."
        f"\nPlease run pacman -R python in msys2."
        f"\n(Current path: {sys.executable})"
    )

REPO = "https://github.com/encounter/decomp-toolkit"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tag_file", help="file containing GitHub tag")
    parser.add_argument("output", type=Path, help="output file path")
    args = parser.parse_args()

    with open(args.tag_file, "r") as f:
        tag = f.readline().rstrip()

    uname = platform.uname()
    suffix = ""
    system = uname.system.lower()
    if system == "darwin":
        system = "macos"
    elif system == "windows":
        suffix = ".exe"
    arch = uname.machine.lower()
    if arch == "amd64":
        arch = "x86_64"

    url = f"{REPO}/releases/download/{tag}/dtk-{system}-{arch}{suffix}"
    output = cast(Path, args.output)
    print(f"Downloading {url} to {output}")
    urllib.request.urlretrieve(url, output)
    output.chmod(0o755)


if __name__ == "__main__":
    main()
