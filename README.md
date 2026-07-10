# Installing Python packages on tiCrypt

Scripts for migrating Python packages onto the air-gapped tiCrypt system, mirroring
the download &rarr; transfer &rarr; offline-install pattern used by
[`install_r`](https://github.com/milechin/install_r).

Unlike `install_r`, this repo does not build Python itself from source &mdash; both
tiCrypt and the BU SCC use the same environment-module Python
(`module load python3/3.13.8`). See [`plan.md`](plan.md) for the environment
discovery behind that assumption, including why the download machine's older
AlmaLinux 8 and tiCrypt's AlmaLinux 9 don't require manual `--platform`/`--abi`
flags.

## Usage

On the machine whose packages you want to replicate:

```bash
python3 install_packages/list_packages.py requirements.txt
```

On an internet-connected machine with the same Python version loaded
(e.g. an SCC compute node with `module load python3/3.13.8`):

```bash
python3 install_packages/install_packages.py download requirements.txt
```

Copy the resulting `DIST/` folder to tiCrypt, then on tiCrypt:

```bash
module load python3/3.13.8
python3 install_packages/install_packages.py offline requirements.txt
```

See [`install_packages/install_packages.py`](install_packages/install_packages.py)
for the full mode list and environment knobs (`DIST_DIR`, `PYPI_REPO`,
`TARGET_PYTHON_VERSION`, `TARGET_PLATFORM`, `TARGET_ABI`).
