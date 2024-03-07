#!/usr/bin/env python3

import json
import pprint
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set


@dataclass
class Archive:
    src: Path
    dst: Path
    manifest: Set[Path]


@dataclass
class Object:
    src: Path
    base: Path
    target: Path
    dwarf: Path
    mwcc: Path
    cflags: List[str]


# TODO name
@dataclass
class Unit:
    complete: bool
    name: str
    signed_char: bool = False


@dataclass
class Profile:
    name: str
    archive_suffix: str
    cflags: List[str]


# CHARFLAGS := -char unsigned

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

# INCLUDES := -Iinclude -ir src

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


@dataclass
class ProjectConfig:
    version: str
    src_dir = Path("src")
    build_dir = Path("build")
    orig_dir = Path("orig")
    mwcc = Path("GC/1.2.5")

    @property
    def output_dir(self) -> Path:
        return self.build_dir / self.version

    @property
    def archive_dir(self) -> Path:
        return self.orig_dir / self.version


config = ProjectConfig("DOLSDK-2001-05-22")


@dataclass
class Lib:
    archives: List[Archive]
    objects: List[Object]

    def __init__(self, name: str, *units: Unit) -> None:
        self.archives = []
        self.objects = []
        for profile in PROFILES:

            def make_dir(dir_name: str) -> Path:
                return config.output_dir / dir_name / profile.name / name

            archive_name = f"{name}{profile.archive_suffix}.a"
            target_dir = make_dir("src")
            base_dir = make_dir("obj")
            dwarf_dir = make_dir("dwarf")

            def create_obj(u: Unit):
                obj_name = Path(u.name)
                return Object(
                    src=config.src_dir / name / obj_name,
                    base=base_dir / obj_name.with_suffix(".o"),
                    target=target_dir / obj_name.with_suffix(".o"),
                    dwarf=dwarf_dir / obj_name.with_suffix(".c"),
                    mwcc=Path("GC/1.2.5"),
                    cflags=[
                        f"-char {'signed' if u.signed_char else 'unsigned'}",
                        *profile.cflags,
                    ],
                )

            objects = list(map(create_obj, units))

            self.archives.append(
                Archive(
                    src=config.archive_dir / archive_name,
                    dst=base_dir,
                    manifest=set(o.base.relative_to(base_dir) for o in objects),
                )
            )
            self.objects.extend(objects)


Matching = True
NonMatching = False


libs = [
    Lib(
        "os",
        Unit(NonMatching, "OSReboot.c", signed_char=True),
        Unit(Matching, "OSAlloc.c"),
    )
]


def main():
    pprint.pp(libs)


if __name__ == "__main__":
    main()
