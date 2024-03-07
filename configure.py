#!/usr/bin/env python3

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
    pass


class Lib:
    archives: List[Archive] = []
    objects: List[Object] = []

    def __init__(self, name: str, *objects: List[LibObject]) -> None:
        pass
