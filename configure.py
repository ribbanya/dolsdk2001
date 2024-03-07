#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from typing import List, Mapping, Set


class Archive:
    src: Path
    dst: Path
    manifest: Set[str]


class Object:
    mwcc: Path
    cflags: List[str]
    target: Path
    base: Path
    pass


# TODO name
class LibObject:
    def __init__(self, complete: bool, name: str) -> None:
        pass


class Lib:
    archives: List[Archive] = []
    objects: List[Object] = []

    def __init__(self, name: str, *objects: LibObject) -> None:
        pass


Matching = True
NonMatching = False

libs = [
    Lib(
        "os",
        LibObject(NonMatching, "OSReboot.c"),
        LibObject(Matching, "OSAlloc.c"),
    )
]


def main():
    json.dump(
        libs,
        fp=sys.stdout,
        indent=2,
        default=lambda o: str(o) if isinstance(o, Path) else o.__dict__,
    )
    print()


if __name__ == "__main__":
    main()
