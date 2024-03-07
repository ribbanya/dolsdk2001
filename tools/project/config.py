import io
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

import ninja_syntax

if sys.platform == "cygwin":
    sys.exit(
        f"Cygwin/MSYS2 is not supported."
        f"\nPlease use native Windows Python instead."
        f"\n(Current path: {sys.executable})"
    )



# TODO name
@dataclass
class Unit:
    name: str
    complete: bool
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


@dataclass
class ProjectConfig:
    profiles: List[Profile]
    version: Optional[str] = field(default=None)
    src_dir = Path("src")
    build_dir = Path("build")
    orig_dir = Path("orig")
    mwcc = Path("GC/1.2.5")

    @property
    def output_dir(self) -> Path:
        # return self.build_dir / self.version
        raise NotImplementedError

    @property
    def archive_dir(self) -> Path:
        # return self.orig_dir / self.version
        raise NotImplementedError


@dataclass
class Lib:
    archives: List[Archive]
    objects: List[Object]
    diffs: List[Diff]

    def __init__(self, config: ProjectConfig, name: str, units: Iterable[Unit]) -> None:
        self.archives = []
        self.objects = []
        self.diffs = []

        for profile in config.profiles:

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


@dataclass
class Tool:
    pass


@dataclass
class BuildConfig:
    archives: List[Archive] = field(default_factory=list)
    objects: List[Object] = field(default_factory=list)
    diffs: List[Diff] = field(default_factory=list)
    tools: List[Tool] = field(default_factory=list)


def generate_build() -> None:
    out = io.StringIO()
    n = ninja_syntax.Writer(out)
    n.variable("ninja_required_version", "1.3")
    n.newline()
