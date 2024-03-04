#!/usr/bin/env python3

###
# Generates build files for the project.
# This file also includes the project configuration,
# such as compiler flags and the object matching status.
#
# Usage:
#   python3 configure.py
#   ninja
#
# Append --help to see available options.
###

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from tools.project import (
    Object,
    ProjectConfig,
    calculate_progress,
    check_ok,
    generate_build,
    generate_objdiff_config,
    is_windows,
)

DEFAULT_REVISION = 36
REVISIONS = {
    36: "2001-05-22",
    # 37: "2001-07-19",
}
REVISION_KEYS = list(map(str, REVISIONS.keys()))

if len(REVISION_KEYS) > 1:
    revisions_str = ", ".join(REVISION_KEYS[:-1]) + f" or {REVISION_KEYS[-1]}"
else:
    revisions_str = REVISION_KEYS[0]

parser = argparse.ArgumentParser()
parser.add_argument(
    "mode",
    default="configure",
    help="configure or progress (default: configure)",
    nargs="?",
)
parser.add_argument(
    "--revision",
    dest="revision",
    type=int,
    default=DEFAULT_REVISION,
    help=f"revision to build ({revisions_str})",
)
parser.add_argument(
    "--build-dir",
    dest="build_dir",
    type=Path,
    default=Path("build"),
    help="base build directory (default: build)",
)
parser.add_argument(
    "--compilers",
    dest="compilers",
    type=Path,
    help="path to compilers (optional)",
)
parser.add_argument(
    "--map",
    dest="map",
    action="store_true",
    help="generate map file(s)",
)
parser.add_argument(
    "--debug",
    dest="debug",
    action="store_true",
    help="build with debug info (non-matching)",
)
if not is_windows():
    parser.add_argument(
        "--wrapper",
        dest="wrapper",
        type=Path,
        help="path to wibo or wine (optional)",
    )
parser.add_argument(
    "--build-dtk",
    dest="build_dtk",
    type=Path,
    help="path to decomp-toolkit source (optional)",
)
parser.add_argument(
    "--sjiswrap",
    dest="sjiswrap",
    type=Path,
    help="path to sjiswrap.exe (optional)",
)
parser.add_argument(
    "--verbose",
    dest="verbose",
    action="store_true",
    help="print verbose output",
)
args = parser.parse_args()

config = ProjectConfig()
if args.revision not in REVISIONS:
    sys.exit(f"Invalid revision '{args.revision}', expected {revisions_str}")
config.version = f"DOLSDK-{REVISIONS[args.revision]}"
config.archive_dir = Path("orig") / config.version

# Apply arguments
config.build_dir = args.build_dir
config.build_dtk_path = args.build_dtk
config.compilers_path = args.compilers
config.debug = args.debug
config.sjiswrap_path = args.sjiswrap
if not is_windows():
    config.wrapper = args.wrapper

# Tool versions
config.compilers_tag = "20231018"
config.dtk_tag = "v0.7.4"
config.sjiswrap_tag = "v1.1.1"
config.wibo_tag = "0.6.9"
config.objdiff_cli_tag = "v1.1.0"


# Base flags, common to most GC/Wii games.
# Generally leave untouched, with overrides added below.
cflags_base = [
    "-cwd source",
    "-nodefaults",
    "-proc gekko",
    "-align powerpc",
    "-enum int",
    "-fp hardware",
    "-Cpp_exceptions off",
    # "-W all",
    "-O4,p",
    "-inline auto",
    '-pragma "cats off"',
    '-pragma "warn_notinlined off"',
    "-maxerrors 1",
    "-nosyspath",
    "-RTTI off",
    "-fp_contract on",
    "-str reuse",
    "-multibyte",  # For Wii compilers, replace with `-enc SJIS`
    "-i include",
    # f"-i build/{config.version}/include",
    f"-DDOLPHIN_REVISION={args.revision}",
]

# Debug flags
if config.debug:
    cflags_base.extend(["-sym on", "-DDEBUG=1"])
else:
    cflags_base.append("-DNDEBUG=1")

# Metrowerks library flags
cflags_runtime = [
    *cflags_base,
    "-use_lmw_stmw on",
    "-str reuse,pool,readonly",
    "-gccinc",
    "-common off",
    "-inline auto",
]

# REL flags
cflags_rel = [
    *cflags_base,
    "-sdata 0",
    "-sdata2 0",
]


def DolphinLib(lib_name: str, objects: List[Object]) -> Dict[str, Any]:
    return {
        "lib": lib_name,
        "archive": (config.archive_dir / lib_name).with_suffix(".a"),
        "mw_version": "GC/1.2.5",
        "cflags": cflags_base,
        "host": False,
        "objects": objects,
    }


Matching = True
NonMatching = False

config.warn_missing_source = False
config.libs = [
    DolphinLib(
        "os",
        [
            Object(Matching, "OSAddress.c"),
            Object(Matching, "OSAlarm.c"),
            Object(Matching, "OSAlloc.c"),
            Object(Matching, "OSArena.c"),
            Object(Matching, "OSAudioSystem.c"),
            Object(Matching, "OSCache.c"),
            Object(Matching, "OSContext.c"),
            Object(Matching, "OSError.c"),
            Object(Matching, "OSExiAd16.c"),
            Object(Matching, "OSExi.c"),
            Object(NonMatching, "OSFont.c"),
            Object(NonMatching, "OSInterrupt.c"),
            Object(Matching, "OSLink.c"),
            Object(Matching, "OSMemory.c"),
            Object(Matching, "OSMessage.c"),
            Object(Matching, "OSMutex.c"),
            Object(Matching, "OS.c"),
            Object(Matching, "OSReset.c"),
            Object(Matching, "OSResetSW.c"),
            Object(Matching, "OSRtc.c"),
            Object(Matching, "OSSerial.c"),
            Object(Matching, "OSStopwatch.c"),
            Object(Matching, "OSSync.c"),
            Object(Matching, "OSThread.c"),
            Object(Matching, "OSTime.c"),
            Object(Matching, "OSTimer.c"),
            Object(Matching, "OSUartExi.c"),
            # TODO
            # Object(Matching, "ppc_eabi_init.c"),
            # Object(Matching, "start.c"),
            # Object(Matching, "time.dolphin.c"),
        ],
    ),
]


# json.dump(
#     config.libs,
#     fp=sys.stdout,
#     default=lambda o: str(o) if isinstance(o, Path) else o.__dict__,
# )

if args.mode == "configure":
    # Write build.ninja and objdiff.json
    generate_build(config)
elif args.mode == "objdiff":
    generate_objdiff_config(config)
elif args.mode == "ok":
    check_ok(config)
# elif args.mode == "progress":
#     # Print progress and write progress.json
#     config.progress_each_module = args.verbose
#     calculate_progress(config)
else:
    sys.exit("Unknown mode: " + args.mode)
