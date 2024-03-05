#!/usr/bin/env python3

###
# Downloads various tools from GitHub releases.
#
# Usage:
#   python3 tools/download_tool.py wibo build/tools/wibo --tag 1.0.0
#
# If changes are made, please submit a PR to
# https://github.com/encounter/dtk-template
###

import argparse
import io
import os
import platform
import shutil
import stat
import urllib.request
import zipfile
from typing import Callable, Dict
from pathlib import Path


def gh_url(repo: str, bin: str, tag: str) -> str:
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

    return f"https://github.com/{repo}/releases/download/{tag}/{bin}-{system}-{arch}{suffix}"


def dtk_url(tag: str) -> str:
    return gh_url("encounter/decomp-toolkit", "dtk", tag)


def objdiff_cli_url(tag: str) -> str:
    return gh_url("ribbanya/objdiff", "objdiff-cli", tag)


def sjiswrap_url(tag: str) -> str:
    repo = "https://github.com/encounter/sjiswrap"
    return f"{repo}/releases/download/{tag}/sjiswrap-windows-x86.exe"


def wibo_url(tag: str) -> str:
    repo = "https://github.com/decompals/wibo"
    return f"{repo}/releases/download/{tag}/wibo"


def compilers_url(tag: str) -> str:
    return f"https://files.decomp.dev/compilers_{tag}.zip"


TOOLS: Dict[str, Callable[[str], str]] = {
    "dtk": dtk_url,
    "sjiswrap": sjiswrap_url,
    "wibo": wibo_url,
    "compilers": compilers_url,
    "objdiff-cli": objdiff_cli_url,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tool", help="Tool name")
    parser.add_argument("output", type=Path, help="output file path")
    parser.add_argument("--tag", help="GitHub tag", required=True)
    args = parser.parse_args()

    url = TOOLS[args.tool](args.tag)
    output = Path(args.output)

    print(f"Downloading {url} to {output}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        if url.endswith(".zip"):
            data = io.BytesIO(response.read())
            with zipfile.ZipFile(data) as f:
                f.extractall(output)
            output.touch(mode=0o755)
        else:
            with open(output, "wb") as f:
                shutil.copyfileobj(response, f)
            st = os.stat(output)
            os.chmod(output, st.st_mode | stat.S_IEXEC)


if __name__ == "__main__":
    main()
