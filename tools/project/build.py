from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Protocol, Set, Tuple

from ninja_syntax import Writer


class NinjaWritable(Protocol):
    def write(self, n: Writer):
        ...


@dataclass
class Rule(NinjaWritable):
    name: str
    command: List[str]

    def write(self, n: Writer):
        n.rule(self.name, self.command)

    def __eq__(self, other):
        if isinstance(other, Rule):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)


@dataclass
class Object(NinjaWritable):
    src: Path
    base: Path
    target: Path
    dwarf: Path
    mwcc: Path
    cflags: List[str]

    def write(self, n: Writer):
        pass


@dataclass
class Archive:
    src: Path
    dst: Path
    manifest: Set[Path]
