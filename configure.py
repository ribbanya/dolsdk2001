#!/usr/bin/env python3

import pprint

from tools.project import Lib, Profile, ProjectConfig, Unit

CFLAGS = [
    "-nodefaults",
    "-proc gekko",
    "-fp hard",
    "-Cpp_exceptions off",
    "-enum int",
    "-warn pragmas",
    "-pragma 'cats off'",
    "-I-",
    "-I include",
    "-ir src",
]


PROFILES = [
    Profile(
        "release",
        archive_suffix="",
        cflags=[
            "-O4,p",
            "-inline auto",
            *CFLAGS,
            "-DRELEASE",
        ],
    ),
    Profile(
        "debug",
        archive_suffix="D",
        cflags=[
            "-opt level=0",
            "-inline off",
            "-schedule off",
            "-sym on",
            *CFLAGS,
            "-DDEBUG",
        ],
    ),
]


config = ProjectConfig(PROFILES)


def lib(name: str, *units: Unit) -> Lib:
    return Lib(config, name, units)


def unit(complete: bool, name: str, signed_char=False):
    return Unit(name, complete, signed_char)


Matching = True
NonMatching = False


LIBS = [
    lib(
        "os",
        unit(NonMatching, "OSReboot.c", signed_char=True),
        unit(Matching, "OSAlloc.c"),
    )
]


def main():
    pass


if __name__ == "__main__":
    main()
