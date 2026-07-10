#!/usr/bin/env python3
"""
ticrypt_packages.py - move Python packages into the air-gapped tiCrypt environment.

Researcher workflow (two steps):

  1. On ANY internet-connected machine (a laptop, an SCC node, ... - its own OS/
     Python version don't matter, since `download` always resolves wheels for
     tiCrypt's target, not for whatever is running the download):
       python3 ticrypt_packages.py download pandas matplotlib
     -> downloads wheels for those packages plus every dependency (pip resolves
        the closure itself - no manual dependency walk needed), and a copy of
        this script, into a folder (default ./ticrypt_packages).

  2. Copy that one folder into tiCrypt, then there:
       python3 ticrypt_packages/ticrypt_packages.py install
     -> installs from the folder with --no-index, no network access.

Run with no arguments for a reminder of the steps.
"""
import argparse
import json
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

# --- tiCrypt target (RCS maintains these to match tiCrypt's current Python) ---
# `download` resolves and fetches wheels for THIS target regardless of what machine
# or Python version is actually running the download - see ../plan.md for the
# environment discovery (AlmaLinux 9.7, x86_64, glibc 2.34, python3/3.13.8 module)
# behind these values. Update them when tiCrypt's Python module changes.
TICRYPT_PYTHON_VERSION = "3.13"      # major.minor of tiCrypt's python3 module
TICRYPT_IMPLEMENTATION = "cp"        # CPython
TICRYPT_ABI = "cp313"                # pip abi tag for the version above
# Multiple manylinux tags, oldest-first, to maximize wheel coverage: any wheel
# built for an older manylinux glibc baseline also runs on tiCrypt's newer glibc
# 2.34 (manylinux tags are forward-compatible). pip download accepts --platform
# more than once and treats them as a set of acceptable tags (pip >= 21.2).
TICRYPT_PLATFORMS = [
    "manylinux2014_x86_64",
    "manylinux_2_17_x86_64",
    "manylinux_2_28_x86_64",
    "linux_x86_64",
]

DEFAULT_DIR = "ticrypt_packages"
TARGET_FILE = "TICRYPT_TARGET.json"
REQUESTED_FILE = "REQUESTED.txt"

THIS_FILE = Path(__file__).resolve()


def _target_info():
    # The target `download` resolved for - not this machine's own environment,
    # which is irrelevant (download can run anywhere).
    return {
        "python_version": TICRYPT_PYTHON_VERSION,
        "implementation": TICRYPT_IMPLEMENTATION,
        "abi": TICRYPT_ABI,
        "platforms": TICRYPT_PLATFORMS,
    }


def _local_environment():
    # This machine's actual environment - used only by `install`, which runs on
    # tiCrypt itself, to sanity-check it against the recorded target.
    impl = "cp" if sys.implementation.name == "cpython" else sys.implementation.name[:2]
    return {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "implementation": impl,
        "abi": f"{impl}{sys.version_info.major}{sys.version_info.minor}",
        "platform_tag": sysconfig.get_platform().replace("-", "_").replace(".", "_"),
    }


def download(packages, dir=DEFAULT_DIR, index_url=None, allow_sdist=False):
    dest = Path(dir)
    dest.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-m", "pip", "download", "--dest", str(dest)]
    if not allow_sdist:
        # Cross-platform resolution can only fetch prebuilt wheels - it can't build
        # from source for a machine other than the one running pip. Without this,
        # pip may still be able to fetch sdists for packages with static metadata,
        # but building them then depends on tiCrypt's own toolchain (it has gcc).
        cmd += ["--only-binary=:all:"]
    cmd += [
        "--python-version", TICRYPT_PYTHON_VERSION,
        "--implementation", TICRYPT_IMPLEMENTATION,
        "--abi", TICRYPT_ABI,
    ]
    for plat in TICRYPT_PLATFORMS:
        cmd += ["--platform", plat]
    if index_url:
        cmd += ["--index-url", index_url]
    cmd += list(packages)

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    (dest / REQUESTED_FILE).write_text("\n".join(sorted(packages)) + "\n")
    (dest / TARGET_FILE).write_text(json.dumps(_target_info(), indent=2))
    shutil.copy(THIS_FILE, dest / THIS_FILE.name)

    print(
        f"\nDone. Next steps:\n"
        f"  1. Copy the folder '{dest}' into tiCrypt.\n"
        f"  2. Inside tiCrypt:\n"
        f"       python3 {dest}/{THIS_FILE.name} install\n"
    )


def install(dir=DEFAULT_DIR, force=False):
    dest = Path(dir)
    req_file = dest / REQUESTED_FILE
    target_file = dest / TARGET_FILE
    if not req_file.exists():
        sys.exit(f"'{req_file}' not found - is this a folder produced by `download`?")

    requested = [line for line in req_file.read_text().splitlines() if line.strip()]

    if target_file.exists():
        recorded = json.loads(target_file.read_text())
        current = _local_environment()
        # Best-effort: platform is checked as "does any recorded tag share this
        # system's arch/os token", not an exact manylinux-tag match - full manylinux
        # compatibility resolution is what pip itself already did at download time.
        platform_ok = any(
            current["platform_tag"] in p or p in current["platform_tag"]
            for p in recorded.get("platforms", [])
        )
        checks = [
            ("Python version", recorded.get("python_version"), current["python_version"]),
            ("implementation", recorded.get("implementation"), current["implementation"]),
            ("abi", recorded.get("abi"), current["abi"]),
        ]
        mismatches = [(label, want, have) for label, want, have in checks if want != have]
        if not platform_ok:
            mismatches.append(("platform", recorded.get("platforms"), current["platform_tag"]))

        if mismatches and not force:
            lines = "\n".join(
                f"  - {label}: downloaded for {want}, but this system is {have}"
                for label, want, have in mismatches
            )
            sys.exit(
                f"This folder was downloaded for a different environment than this "
                f"system:\n{lines}\n\n"
                f"Packages may fail to install or be incompatible. Update the "
                f"TICRYPT_* constants at the top of this script if tiCrypt's Python "
                f"has changed, re-run `download`, and copy the folder over again - "
                f"or install anyway with `install --force`."
            )
        elif mismatches:
            print("WARNING: proceeding despite an environment mismatch (--force).")
    else:
        print(
            "NOTE: target metadata not recorded in this folder (older download); "
            "skipping compatibility check."
        )

    cmd = [
        sys.executable, "-m", "pip", "install",
        "--no-index", "--find-links", str(dest), *requested,
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="mode")

    p_dl = sub.add_parser("download", help="download packages + dependencies for transfer")
    p_dl.add_argument("packages", nargs="+")
    p_dl.add_argument("--dir", default=DEFAULT_DIR)
    p_dl.add_argument("--index-url")
    p_dl.add_argument(
        "--allow-sdist", action="store_true",
        help="also allow source distributions, not just wheels (tiCrypt has gcc to build them)",
    )

    p_in = sub.add_parser("install", help="install the downloaded packages (no network)")
    p_in.add_argument("--dir", default=DEFAULT_DIR)
    p_in.add_argument("--force", action="store_true")

    args = parser.parse_args()
    if args.mode == "download":
        download(args.packages, dir=args.dir, index_url=args.index_url, allow_sdist=args.allow_sdist)
    elif args.mode == "install":
        install(dir=args.dir, force=args.force)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
