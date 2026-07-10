#!/usr/bin/env python3
"""
Install (or download for air-gapped transfer) Python packages from a requirements file.

Three modes, selected by the first argument:

    python3 install_packages.py online   [requirements.txt]   # install from PyPI (default)
    python3 install_packages.py download [requirements.txt]   # download wheels/sdists -> DIST
    python3 install_packages.py offline  [requirements.txt]   # install from local DIST, no network

If the first argument is not one of those mode keywords it is treated as the
requirements file and the mode defaults to "online", so the shorter form still works:

    python3 install_packages.py [requirements.txt]             # == online

The requirements file defaults to requirements.txt (produced by list_packages.py).

Air-gap workflow:
  1. On an internet-connected machine with the SAME Python version as the target
     (module-loaded, e.g. `module load python3/3.13.8`):
       python3 install_packages.py download requirements.txt
     -> resolves and downloads the full dependency closure into DIST_DIR.
  2. Copy DIST_DIR to the air-gapped target.
  3. On the target:
       python3 install_packages.py offline requirements.txt
     -> installs from DIST_DIR with --no-index --find-links, no network access.

Environment knobs:
  DIST_DIR                 Download/install folder (default: ./DIST)
  PYPI_REPO                PyPI index URL for online/download modes (default: PyPI itself)
  TARGET_PYTHON_VERSION     Optional --python-version for download mode (e.g. 3.13)
  TARGET_PLATFORM           Optional --platform for download mode (e.g. linux_x86_64)
  TARGET_ABI                Optional --abi for download mode (e.g. cp313)

  The TARGET_* knobs are only needed if the download machine's Python
  version/OS/arch doesn't match the target closely enough for pip's default
  (same-machine) resolution to produce compatible wheels. Setting any of them
  forces --only-binary=:all:, since cross-platform resolution can't build
  from source. See ../plan.md for when tiCrypt vs. the download machine did
  or didn't need these.
"""
import os
import subprocess
import sys
from pathlib import Path

MODES = {"online", "download", "offline"}


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
        cmd = [
            sys.executable, "-m", "pip", "download",
            "--dest", str(dist_dir),
            "-r", str(req_file),
        ]
        if repo:
            cmd += ["--index-url", repo]

        py_ver = os.environ.get("TARGET_PYTHON_VERSION")
        platform = os.environ.get("TARGET_PLATFORM")
        abi = os.environ.get("TARGET_ABI")
        if py_ver or platform or abi:
            cmd += ["--only-binary=:all:"]
            if py_ver:
                cmd += ["--python-version", py_ver]
            if platform:
                cmd += ["--platform", platform]
            if abi:
                cmd += ["--abi", abi]

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
