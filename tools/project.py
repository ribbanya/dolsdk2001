###
# decomp-toolkit project generator
# Generates build.ninja and objdiff.json.
#
# This generator is intentionally project-agnostic
# and shared between multiple projects. Any configuration
# specific to a project should be added to `configure.py`.
#
# If changes are made, please submit a PR to
# https://github.com/encounter/dtk-template
###

import io
import json
import math
import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

from . import ninja_syntax

if sys.platform == "cygwin":
    sys.exit(
        f"Cygwin/MSYS2 is not supported."
        f"\nPlease use native Windows Python instead."
        f"\n(Current path: {sys.executable})"
    )


class Object:
    def __init__(self, completed: bool, name: str, **options: Any) -> None:
        self.name = name
        self.completed = completed
        self.options: Dict[str, Any] = {
            "add_to_all": True,
            "cflags": None,
            "extra_cflags": None,
            "mw_version": None,
            "shiftjis": True,
            "source": name,
        }
        self.options.update(options)


class ProjectConfig:
    def __init__(self) -> None:
        # Paths
        self.build_dir: Path = Path("build")
        self.src_dir: Path = Path("src")
        self.tools_dir: Path = Path("tools")
        self.archive_dir: Path

        # Tooling
        self.dtk_tag: Optional[str] = None  # Git tag
        self.build_dtk_path: Optional[Path] = None  # If None, download
        self.compilers_tag: Optional[str] = None  # 1
        self.compilers_path: Optional[Path] = None  # If None, download
        self.wibo_tag: Optional[str] = None  # Git tag
        self.wrapper: Optional[Path] = None  # If None, download wibo on Linux
        self.sjiswrap_tag: Optional[str] = None  # Git tag
        self.sjiswrap_path: Optional[Path] = None  # If None, download

        # Project config
        self.debug: bool = False  # Build with debug info
        self.libs: Optional[List[Dict[str, Any]]] = None  # List of libraries
        self.version: Optional[str] = None  # Version name
        self.warn_missing_source: bool = False  # Warn on missing source file

        # Progress output and progress.json config
        self.progress_all: bool = True  # Include combined "all" category
        self.progress_modules: bool = True  # Include combined "modules" category
        self.progress_each_module: bool = (
            True  # Include individual modules, disable for large numbers of modules
        )

        # Progress fancy printing
        self.progress_use_fancy: bool = False
        self.progress_code_fancy_frac: int = 0
        self.progress_code_fancy_item: str = ""
        self.progress_data_fancy_frac: int = 0
        self.progress_data_fancy_item: str = ""

    def validate(self) -> None:
        required_attrs = [
            "build_dir",
            "src_dir",
            "tools_dir",
            "archive_dir",
            "libs",
            "version",
        ]
        for attr in required_attrs:
            if getattr(self, attr) is None:
                sys.exit(f"ProjectConfig.{attr} missing")

    def find_object(self, name: str) -> Optional[Tuple[Dict[str, Any], Object]]:
        for lib in self.libs or {}:
            for obj in lib["objects"]:
                if obj.name == name:
                    return lib, obj
        return None

    def out_path(self) -> Path:
        return self.build_dir / str(self.version)


def is_windows() -> bool:
    return os.name == "nt"


# On Windows, we need this to use && in commands
CHAIN = "cmd /c " if is_windows() else ""
# Native executable extension
EXE = ".exe" if is_windows() else ""


# Generate build.ninja and objdiff.json
def generate_build(config: ProjectConfig) -> None:
    generate_build_ninja(config)
    generate_objdiff_config(config)


# Generate build.ninja
def generate_build_ninja(config: ProjectConfig) -> None:
    config.validate()

    out = io.StringIO()
    n = ninja_syntax.Writer(out)
    n.variable("ninja_required_version", "1.3")
    n.newline()

    configure_script = Path(os.path.relpath(os.path.abspath(sys.argv[0])))
    python_lib = Path(os.path.relpath(__file__))
    python_lib_dir = python_lib.parent
    n.comment("The arguments passed to configure.py, for rerunning it.")
    n.variable("configure_args", sys.argv[1:])
    n.variable("python", f'"{sys.executable}"')
    n.newline()

    ###
    # Tooling
    ###
    n.comment("Tooling")

    build_path = config.out_path()
    progress_path = build_path / "progress.json"
    build_tools_path = config.build_dir / "tools"
    download_tool = config.tools_dir / "download_tool.py"
    n.rule(
        name="download_tool",
        command=f"$python {download_tool} $tool $out --tag $tag",
        description="TOOL $out",
    )

    if config.build_dtk_path:
        dtk = build_tools_path / "release" / f"dtk{EXE}"
        n.rule(
            name="cargo",
            command="cargo build --release --manifest-path $in --bin $bin --target-dir $target",
            description="CARGO $bin",
            depfile=Path("$target") / "release" / "$bin.d",
            deps="gcc",
        )
        n.build(
            outputs=dtk,
            rule="cargo",
            inputs=config.build_dtk_path / "Cargo.toml",
            implicit=config.build_dtk_path / "Cargo.lock",
            variables={
                "bin": "dtk",
                "target": build_tools_path,
            },
        )
    elif config.dtk_tag:
        dtk = build_tools_path / f"dtk{EXE}"
        n.build(
            outputs=dtk,
            rule="download_tool",
            implicit=download_tool,
            variables={
                "tool": "dtk",
                "tag": config.dtk_tag,
            },
        )
    else:
        sys.exit("ProjectConfig.dtk_tag missing")

    if config.sjiswrap_path:
        sjiswrap = config.sjiswrap_path
    elif config.sjiswrap_tag:
        sjiswrap = build_tools_path / "sjiswrap.exe"
        n.build(
            outputs=sjiswrap,
            rule="download_tool",
            implicit=download_tool,
            variables={
                "tool": "sjiswrap",
                "tag": config.sjiswrap_tag,
            },
        )
    else:
        sys.exit("ProjectConfig.sjiswrap_tag missing")

    # Only add an implicit dependency on wibo if we download it
    wrapper = config.wrapper
    wrapper_implicit: Optional[Path] = None
    if (
        config.wibo_tag is not None
        and sys.platform == "linux"
        and platform.machine() in ("i386", "x86_64")
        and config.wrapper is None
    ):
        wrapper = build_tools_path / "wibo"
        wrapper_implicit = wrapper
        n.build(
            outputs=wrapper,
            rule="download_tool",
            implicit=download_tool,
            variables={
                "tool": "wibo",
                "tag": config.wibo_tag,
            },
        )
    if not is_windows() and wrapper is None:
        wrapper = Path("wine")
    wrapper_cmd = f"{wrapper} " if wrapper else ""

    compilers_implicit: Optional[Path] = None
    if config.compilers_path:
        compilers = config.compilers_path
    elif config.compilers_tag:
        compilers = config.build_dir / "compilers"
        compilers_implicit = compilers
        n.build(
            outputs=compilers,
            rule="download_tool",
            implicit=download_tool,
            variables={
                "tool": "compilers",
                "tag": config.compilers_tag,
            },
        )
    else:
        sys.exit("ProjectConfig.compilers_tag missing")

    n.newline()

    ###
    # Build rules
    ###
    compiler_path = compilers / "$mw_version"

    # MWCC
    mwcc = compiler_path / "mwcceppc.exe"
    mwcc_cmd = f"{wrapper_cmd}{mwcc} $cflags -MMD -c $in -o $basedir"
    mwcc_implicit: List[Optional[Path]] = [compilers_implicit or mwcc, wrapper_implicit]

    # MWCC with UTF-8 to Shift JIS wrapper
    mwcc_sjis_cmd = f"{wrapper_cmd}{sjiswrap} {mwcc} $cflags -MMD -c $in -o $basedir"
    mwcc_sjis_implicit: List[Optional[Path]] = [*mwcc_implicit, sjiswrap]

    if os.name != "nt":
        transform_dep = config.tools_dir / "transform_dep.py"
        mwcc_cmd += f" && $python {transform_dep} $basefile.d $basefile.d"
        mwcc_sjis_cmd += f" && $python {transform_dep} $basefile.d $basefile.d"
        mwcc_implicit.append(transform_dep)
        mwcc_sjis_implicit.append(transform_dep)

    n.comment("MWCC build")
    n.rule(
        name="mwcc",
        command=mwcc_cmd,
        description="MWCC $out",
        depfile="$basefile.d",
        deps="gcc",
    )
    n.newline()

    n.comment("MWCC build (with UTF-8 to Shift JIS wrapper)")
    n.rule(
        name="mwcc_sjis",
        command=mwcc_sjis_cmd,
        description="MWCC $out",
        depfile="$basefile.d",
        deps="gcc",
    )
    n.newline()

    n.comment("Host build")
    n.variable("host_cflags", "-I include -Wno-trigraphs")
    n.variable(
        "host_cppflags",
        "-std=c++98 -I include -fno-exceptions -fno-rtti -D_CRT_SECURE_NO_WARNINGS -Wno-trigraphs -Wno-c++11-extensions",
    )
    n.rule(
        name="host_cc",
        command="clang $host_cflags -c -o $out $in",
        description="CC $out",
    )
    n.rule(
        name="host_cpp",
        command="clang++ $host_cppflags -c -o $out $in",
        description="CXX $out",
    )
    n.newline()

    ###
    # Source files
    ###
    n.comment("Source files")
    build_src_path = build_path / "src"

    used_compiler_versions: Set[str] = set()
    # TODO
    source_inputs: List[Path] = []

    # Check if all compiler versions exist
    for mw_version in used_compiler_versions:
        mw_path = compilers / mw_version / "mwcceppc.exe"
        if config.compilers_path and not os.path.exists(mw_path):
            sys.exit(f"Compiler {mw_path} does not exist")

    # HACK: Figure out something better, especially when objdiff gets build profiles
    profiles = ["debug", "release"]

    ###
    # Extract archives
    #
    n.comment("Extract library archives")
    n.rule(
        name="ar_extract",
        command=f"{dtk} ar extract $in -o $basedir",
        description="EXTRACT $in",
    )
    n.newline()

    n.comment("Disassemble object")
    n.rule(
        name="elf_disasm",
        command=f"{dtk} elf disasm $in $out",
        description="DISASM $out",
    )
    n.newline()

    n.comment("Dump DWARF info")
    n.rule(
        name="dwarf_dump",
        command=f"{dtk} dwarf dump $in -o $out",
        description="DWARF $out",
    )
    n.newline()

    for lib in filter(lambda l: l.get("archive") is not None, config.libs or []):
        for profile in profiles:
            archive = cast(Path, lib["archive"])
            basedir = config.out_path() / profile / lib["lib"]

            # HACK
            if profile == "debug":
                archive = archive.with_stem(f"{archive.stem}D")

            outputs = []
            obj: Object
            n.comment("Extract archive")
            for obj in lib.get("objects", []):
                outputs.append(
                    (basedir / Path(obj.name).name).with_suffix(".o"),
                )
            n.build(
                outputs=outputs,
                rule="ar_extract",
                inputs=archive,
                variables={"basedir": basedir},
                implicit=dtk,
            )
            n.newline()

            for input in outputs:
                n.comment(str(input))
                n.build(
                    outputs=input.with_suffix(".s"),
                    rule="elf_disasm",
                    inputs=input,
                )
                n.build(
                    outputs=input.with_name(f"{input.stem}_DWARF.c"),
                    rule="dwarf_dump",
                    inputs=input,
                )
                n.newline()


    ###
    # Helper rule for building all source files
    ###
    # TODO
    # n.comment("Build all source files")
    # n.build(
    #     outputs="all_source",
    #     rule="phony",
    #     inputs=source_inputs,
    # )
    # n.newline()

    ###
    # Check hash
    ###
    # TODO objdiff-cli

    ###
    # Calculate progress
    ###
    # TODO objdiff-cli
    ###

    # Helper tools (diff)
    ###
    # TODO objdiff-cli
    # TODO: make these rules work for RELs too

    ###
    # Regenerate on change
    ###
    n.comment("Reconfigure on change")
    n.rule(
        name="configure",
        command=f"$python {configure_script} $configure_args",
        generator=True,
        description=f"RUN {configure_script}",
    )
    n.build(
        outputs="build.ninja",
        rule="configure",
        implicit=[
            configure_script,
            python_lib,
            python_lib_dir / "ninja_syntax.py",
        ],
    )
    n.newline()

    ###
    # Default rule
    ###
    # TODO
    # n.comment("Default rule")
    # if build_config:
    #     n.default(progress_path)
    # else:
    #     n.default(build_config_path)

    # Write build.ninja
    with open("build.ninja", "w", encoding="utf-8") as f:
        f.write(out.getvalue())
    out.close()


# Generate objdiff.json
def generate_objdiff_config(config: ProjectConfig) -> None:
    objdiff_config: Dict[str, Any] = {
        "min_version": "0.4.3",
        "custom_make": "ninja",
        "build_target": False,
        "watch_patterns": [
            "*.c",
            "*.cp",
            "*.cpp",
            "*.h",
            "*.hpp",
            "*.inc",
            "*.py",
            "*.yml",
            "*.txt",
            "*.json",
        ],
        "units": [],
    }

    build_path = config.out_path()

    def add_unit(build_obj: Dict[str, Any], module_name: str) -> None:
        if build_obj["autogenerated"]:
            # Skip autogenerated objects
            return

        obj_path, obj_name = build_obj["object"], build_obj["name"]
        base_object = Path(obj_name).with_suffix("")
        unit_config: Dict[str, Any] = {
            "name": Path(module_name) / base_object,
            "target_path": obj_path,
        }

        result = config.find_object(obj_name)
        if not result:
            objdiff_config["units"].append(unit_config)
            return

        lib, obj = result
        src_dir = Path(lib.get("src_dir", config.src_dir))

        unit_src_path = src_dir / str(obj.options["source"])

        if not unit_src_path.exists():
            objdiff_config["units"].append(unit_config)
            return

        cflags = obj.options["cflags"] or lib["cflags"]
        src_obj_path = build_path / "src" / f"{base_object}.o"

        reverse_fn_order = False
        if type(cflags) is list:
            for flag in cflags:
                if not flag.startswith("-inline "):
                    continue
                for value in flag.split(" ")[1].split(","):
                    if value == "deferred":
                        reverse_fn_order = True
                    elif value == "nodeferred":
                        reverse_fn_order = False

        unit_config["base_path"] = src_obj_path
        unit_config["reverse_fn_order"] = reverse_fn_order
        unit_config["complete"] = obj.completed
        objdiff_config["units"].append(unit_config)

    # Write objdiff.json
    with open("objdiff.json", "w", encoding="utf-8") as w:
        from .ninja_syntax import serialize_path

        json.dump(objdiff_config, w, indent=4, default=serialize_path)


# Calculate, print and write progress to progress.json
def calculate_progress(config: ProjectConfig) -> None:
    pass
    # TODO
    # out_path = config.out_path()

    # class ProgressUnit:
    #     def __init__(self, name: str) -> None:
    #         self.name: str = name
    #         self.code_total: int = 0
    #         self.code_fancy_frac: int = config.progress_code_fancy_frac
    #         self.code_fancy_item: str = config.progress_code_fancy_item
    #         self.code_progress: int = 0
    #         self.data_total: int = 0
    #         self.data_fancy_frac: int = config.progress_data_fancy_frac
    #         self.data_fancy_item: str = config.progress_data_fancy_item
    #         self.data_progress: int = 0
    #         self.objects_progress: int = 0
    #         self.objects_total: int = 0
    #         self.objects: Set[Object] = set()

    #     def add(self, build_obj: Dict[str, Any]) -> None:
    #         self.code_total += build_obj["code_size"]
    #         self.data_total += build_obj["data_size"]

    #         # Avoid counting the same object in different modules twice
    #         include_object = build_obj["name"] not in self.objects
    #         if include_object:
    #             self.objects.add(build_obj["name"])
    #             self.objects_total += 1

    #         if build_obj["autogenerated"]:
    #             # Skip autogenerated objects
    #             return

    #         result = config.find_object(build_obj["name"])
    #         if not result:
    #             return

    #         _, obj = result
    #         if not obj.completed:
    #             return

    #         self.code_progress += build_obj["code_size"]
    #         self.data_progress += build_obj["data_size"]
    #         if include_object:
    #             self.objects_progress += 1

    #     def code_frac(self) -> float:
    #         return self.code_progress / self.code_total

    #     def data_frac(self) -> float:
    #         return self.data_progress / self.data_total

    # # Add DOL units
    # all_progress = ProgressUnit("All") if config.progress_all else None
    # dol_progress = ProgressUnit("DOL")
    # for unit in build_config["units"]:
    #     if all_progress:
    #         all_progress.add(unit)
    #     dol_progress.add(unit)

    # # Add REL units
    # rels_progress = ProgressUnit("Modules") if config.progress_modules else None
    # modules_progress: List[ProgressUnit] = []
    # for module in build_config["modules"]:
    #     progress = ProgressUnit(module["name"])
    #     modules_progress.append(progress)
    #     for unit in module["units"]:
    #         if all_progress:
    #             all_progress.add(unit)
    #         if rels_progress:
    #             rels_progress.add(unit)
    #         progress.add(unit)

    # # Print human-readable progress
    # print("Progress:")

    # def print_category(unit: Optional[ProgressUnit]) -> None:
    #     if unit is None:
    #         return

    #     code_frac = unit.code_frac()
    #     data_frac = unit.data_frac()
    #     print(
    #         f"  {unit.name}: {code_frac:.2%} code, {data_frac:.2%} data ({unit.objects_progress} / {unit.objects_total} files)"
    #     )
    #     print(f"    Code: {unit.code_progress} / {unit.code_total} bytes")
    #     print(f"    Data: {unit.data_progress} / {unit.data_total} bytes")
    #     if config.progress_use_fancy:
    #         print(
    #             "\nYou have {} out of {} {} and collected {} out of {} {}.".format(
    #                 math.floor(code_frac * unit.code_fancy_frac),
    #                 unit.code_fancy_frac,
    #                 unit.code_fancy_item,
    #                 math.floor(data_frac * unit.data_fancy_frac),
    #                 unit.data_fancy_frac,
    #                 unit.data_fancy_item,
    #             )
    #         )

    # if all_progress:
    #     print_category(all_progress)
    # print_category(dol_progress)
    # module_count = len(build_config["modules"])
    # if module_count > 0:
    #     print_category(rels_progress)
    #     if config.progress_each_module:
    #         for progress in modules_progress:
    #             print_category(progress)

    # # Generate and write progress.json
    # progress_json: Dict[str, Any] = {}

    # def add_category(category: str, unit: ProgressUnit) -> None:
    #     progress_json[category] = {
    #         "code": unit.code_progress,
    #         "code/total": unit.code_total,
    #         "data": unit.data_progress,
    #         "data/total": unit.data_total,
    #     }

    # if all_progress:
    #     add_category("all", all_progress)
    # add_category("dol", dol_progress)
    # if len(build_config["modules"]) > 0:
    #     if rels_progress:
    #         add_category("modules", rels_progress)
    #     if config.progress_each_module:
    #         for progress in modules_progress:
    #             add_category(progress.name, progress)
    # with open(out_path / "progress.json", "w", encoding="utf-8") as w:
    #     json.dump(progress_json, w, indent=4)
