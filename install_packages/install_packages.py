#!/usr/bin/env python3
"""
Install (or download for air-gapped transfer) Python packages from a requirements file.

Three modes, selected by the first argument:

    python3 install_packages.py online   [requirements.txt]   # install from PyPI (default)
    python3 install_packages.py download [requirements.txt]   # download wheels -> DIST
    python3 install_packages.py offline  [requirements.txt]   # install from local DIST, no network

If the first argument is not one of those mode keywords it is treated as the
requirements file and the mode defaults to "online", so the shorter form still works:

    python3 install_packages.py [requirements.txt]             # == online

The requirements file defaults to requirements.txt (produced by list_packages.py).

Air-gap workflow:
  1. On ANY internet-connected machine (its own OS/Python version don't matter -
     download always resolves wheels for the TARGET_* below, not for whatever is
     running the download):
       python3 install_packages.py download requirements.txt
     -> resolves and downloads the full dependency closure into DIST_DIR.
  2. Copy DIST_DIR to the air-gapped target.
  3. On the target:
       python3 install_packages.py offline requirements.txt
     -> installs from DIST_DIR with --no-index --find-links, no network access.

Environment knobs:
  DIST_DIR                Download/install folder (default: ./DIST)
  PYPI_REPO               PyPI index URL for online/download modes (default: PyPI itself)
  TARGET_PYTHON_VERSION   --python-version for download mode (default: 3.13)
  TARGET_IMPLEMENTATION   --implementation for download mode (default: cp = CPython)
  TARGET_ABI              --abi for download mode (default: cp313)
  TARGET_PLATFORMS        comma-separated --platform values for download mode
                          (default: manylinux2014_x86_64,manylinux_2_17_x86_64,
                          manylinux_2_28_x86_64,linux_x86_64 - see ../plan.md for why
                          this list, not just one tag)
  ALLOW_SDIST             set to 1 to also allow source distributions, not just wheels
                          (the target needs a compatible compiler - tiCrypt has gcc)

  The TARGET_* defaults describe tiCrypt (RCS-maintained - update them if tiCrypt's
  Python module changes). download always resolves against them regardless of what
  machine/Python version is actually running it.
"""
import os
import subprocess
import sys
from pathlib import Path

MODES = {"online", "download", "offline"}

DEFAULT_TARGET_PYTHON_VERSION = "3.13"
DEFAULT_TARGET_IMPLEMENTATION = "cp"
DEFAULT_TARGET_ABI = "cp313"
DEFAULT_TARGET_PLATFORMS = (
    "manylinux2014_x86_64,manylinux_2_17_x86_64,manylinux_2_28_x86_64,linux_x86_64"
)


def main():
    args = sys.argv[1:]
    mode = "online"
    if args and args[0] in MODES:
        mode = args.pop(0)
    req_file = Path(args[0]) if args else Path("requirements.txt")
    dist_dir = Path(os.environ.get("DIST_DIR", "DIST"))
    repo = os.environ.get("PYPI_REPO")

    if mode == "online":
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
        if repo:
            cmd += ["--index-url", repo]

    elif mode == "download":
        dist_dir.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, "-m", "pip", "download", "--dest", str(dist_dir)]

        if not os.environ.get("ALLOW_SDIST"):
            cmd += ["--only-binary=:all:"]

        py_ver = os.environ.get("TARGET_PYTHON_VERSION", DEFAULT_TARGET_PYTHON_VERSION)
        impl = os.environ.get("TARGET_IMPLEMENTATION", DEFAULT_TARGET_IMPLEMENTATION)
        abi = os.environ.get("TARGET_ABI", DEFAULT_TARGET_ABI)
        platforms = os.environ.get("TARGET_PLATFORMS", DEFAULT_TARGET_PLATFORMS)
        cmd += ["--python-version", py_ver, "--implementation", impl, "--abi", abi]
        for plat in platforms.split(","):
            cmd += ["--platform", plat.strip()]

        if repo:
            cmd += ["--index-url", repo]
        cmd += ["-r", str(req_file)]

    elif mode == "offline":
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--no-index", "--find-links", str(dist_dir),
            "-r", str(req_file),
        ]

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
