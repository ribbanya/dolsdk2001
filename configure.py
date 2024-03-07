#!/usr/bin/env python3

import pprint
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set, Tuple


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


@dataclass
class Diff:
    name: str
    target_path: Path
    base_path: Path
    reverse_fn_order: bool
    complete: bool


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
    diffs: List[Diff]

    def __init__(self, name: str, *units: Unit) -> None:
        self.archives = []
        self.objects = []
        self.diffs = []

        for profile in PROFILES:

            def make_dir(dir_name: str) -> Path:
                return config.output_dir / dir_name / profile.name / name

            archive_name = f"{name}{profile.archive_suffix}.a"
            target_dir = make_dir("src")
            base_dir = make_dir("obj")
            dwarf_dir = make_dir("dwarf")

            def create_pair(u: Unit) -> Tuple[Object, Diff]:
                src_name = Path(u.name)
                obj_name = src_name.with_suffix(".o")
                base_path = base_dir / obj_name
                target_path = target_dir / obj_name
                obj = Object(
                    src=config.src_dir / name / src_name,
                    base=base_path,
                    target=target_path,
                    dwarf=dwarf_dir / src_name.with_suffix(".c"),
                    mwcc=Path("GC/1.2.5"),
                    cflags=[
                        f"-char {'signed' if u.signed_char else 'unsigned'}",
                        *profile.cflags,
                    ],
                )

                diff = Diff(
                    name=str(
                        (Path(profile.name) / name / src_name)
                        .with_suffix("")
                        .as_posix()
                    ),
                    target_path=target_path,
                    base_path=base_path,
                    reverse_fn_order=False,
                    complete=u.complete,
                )

                return obj, diff

            pairs = list(map(create_pair, units))

            self.archives.append(
                Archive(
                    src=config.archive_dir / archive_name,
                    dst=base_dir,
                    manifest=set(o.base.relative_to(base_dir) for o, _ in pairs),
                )
            )
            self.objects.extend(obj for obj, _ in pairs)
            self.diffs.extend(diff for _, diff in pairs)


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
