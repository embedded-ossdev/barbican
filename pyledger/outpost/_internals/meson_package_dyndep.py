# SPDX-FileCopyrightText: 2024 Ledger SAS
# SPDX-License-Identifier: Apache-2.0


from argparse import ArgumentParser
import json
from pathlib import Path
import subprocess
import typing as T

from ..utils.environment import find_program


def _add_build_target_dyndep(
    target: str, implicit_inputs: set[str], implicit_output: set[str], out: T.Any
) -> None:
    """Add dynamically generated implicit ins/outs for a given target

    ..notes: The target must exists in the top level build.ninja file

    Ninja dyndep are formatted as follow:
     - build <target> [| [<implicit outs> ...]]: dyndep [| [<implicit ins>...] ]
    """
    out.write(f"build {target}")
    if implicit_output:
        out.write(" |")
    for f in implicit_output:
        out.write(f" $\n {f}")

    out.write(": dyndep")

    if implicit_inputs:
        out.write(" |")
    for f in implicit_inputs:
        out.write(f" $\n {f}")
    out.write("\n")
    out.write("  restat = 1\n")


def _gen_ninja_dyndep_file(
    package: str, introspect: T.Any, stagingdir: Path, output: T.Any
) -> None:
    """Generate dyndep file

    For compile target, build system files and sources file are needed as implicit inputs.
    Files to be installed are implicit output (resp. inputs) of compile (resp. install) command.
    ..notes: if inner build system files change, a reconfigure and rebuild is triggered.
    ..warning: some outputs are internal targets input, thus remove installed file from implicit
    inputs.
    """

    compile_target = f"{package}_compile.stamp"
    install_target = f"{package}_install.stamp"

    package_buildsys_files = introspect["buildsystem_files"]
    package_sources = []
    for target in introspect["targets"]:
        if "target_sources" in target:
            for target_sources in target["target_sources"]:
                if "sources" in target_sources:
                    package_sources.extend(target_sources["sources"])
                if "generated_sources" in target_sources:
                    package_sources.extend(target_sources["generated_sources"])

    installed = introspect["installed"]

    compile_implicit_outputs = set(installed.keys())
    compile_implicit_inputs = set(package_buildsys_files + package_sources)
    compile_implicit_inputs.difference_update(compile_implicit_outputs)

    install_implicit_inputs = compile_implicit_outputs
    install_implicit_outputs = set([stagingdir / f[1:] for f in installed.values()])

    with output.open("w") as dyndep:
        dyndep.write("ninja_dyndep_version = 1\n")
        _add_build_target_dyndep(
            compile_target, compile_implicit_inputs, compile_implicit_outputs, dyndep
        )
        _add_build_target_dyndep(
            install_target, install_implicit_inputs, install_implicit_outputs, dyndep
        )


def run_meson_package_dyndep(
    name: str, builddir: Path, stagingdir: Path, dyndep: Path, outfile: Path
) -> None:
    """Generate a ninja dynamic dependencies file for a meson package.

    This will populated implicit inputs and outputs of the given meson package
    using meson introspection.

    for a meson target, the following build rules are generated:
     - <name>_setup
     - <name>_compile[.stamp]
     - <name>_install[.stamp]

    This command generate a ninja dyndep file for compile and install target
    """
    meson = find_program("meson")
    cmdline = [meson, "introspect", "--all", "-i", str(builddir.resolve(strict=True))]
    proc_return = subprocess.run(cmdline, check=True, capture_output=True)
    package_introspection = json.loads(proc_return.stdout)

    _gen_ninja_dyndep_file(name, package_introspection, stagingdir, dyndep)


def run(argv: T.List[str]) -> None:
    """Execute meson package dyndep internal command"""
    parser = ArgumentParser()
    parser.add_argument("--name", type=str, action="store", help="package name")
    parser.add_argument(
        "-j",
        "--json",
        type=Path,
        required=True,
        help="save meson package introspection data to file (json formatted)",
    )
    parser.add_argument("builddir", type=Path, help="package builddir")
    parser.add_argument("stagingdir", type=Path, help="package stagingdir")
    parser.add_argument("dyndep", type=Path, help="dynamic dependencies file")

    args = parser.parse_args(argv)
    run_meson_package_dyndep(args.name, args.builddir, args.stagingdir, args.dyndep, args.json)
