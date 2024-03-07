import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Protocol, Set, Tuple

import ninja_syntax
from ninja_syntax import Writer

from tools.project.cli import Args

from .config import Lib, ProjectConfig, Unit


class NinjaWritable(Protocol):
    def write(self, n: Writer):
        ...


@dataclass
class Rule(NinjaWritable):
    name: str
    command: str
    description: Optional[str] = field(default=None)

    def write(self, n: Writer):
        n.rule(self.name, self.command, self.description)

    def __eq__(self, other) -> bool:
        return isinstance(other, Rule) and self.name == other.name

    def __hash__(self) -> int:
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
        raise NotImplementedError

    @classmethod
    def from_unit(cls, unit: Unit, config: ProjectConfig, args: Args):
        raise NotImplementedError


@dataclass
class Archive:
    src: Path
    dst: Path
    manifest: Set[Path]

    def write(self, n: Writer):
        raise NotImplementedError


def generate_steps(args: Args, config: ProjectConfig):
    raise NotImplementedError


def generate_build(steps: Iterable[NinjaWritable]) -> None:
    with io.StringIO() as out:
        n = ninja_syntax.Writer(out)

        for step in steps:
            step.write(n)

        out_path = Path(__file__) / "build.ninja"
        with out_path.open("w", encoding="utf-8") as f:
            f.write(out.getvalue())
