#!/usr/bin/env python3
"""
List installed (non-stdlib) Python packages into a requirements file.

Thin wrapper around `pip freeze`, which already excludes stdlib modules (they
aren't installed via pip) and pip/setuptools/wheel themselves. Output feeds
install_packages.py's download step.

Usage:
    python3 list_packages.py [requirements.txt]
"""
import subprocess
import sys
from pathlib import Path


def main():
    output_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("requirements.txt")

    result = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        check=True, capture_output=True, text=True,
    )

    output_file.write_text(result.stdout)
    n = len([line for line in result.stdout.splitlines() if line.strip()])
    print(f"Successfully listed {n} installed packages in {output_file}")


if __name__ == "__main__":
    main()
