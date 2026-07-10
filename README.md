# Installing Python packages on tiCrypt

Scripts for migrating Python packages onto the air-gapped tiCrypt system, mirroring
the download &rarr; transfer &rarr; offline-install pattern used by
[`install_r`](https://github.com/milechin/install_r).

Unlike `install_r`, this repo does not build Python itself from source &mdash;
tiCrypt uses an environment-module Python (`module load python3/3.13.8`). The
**download step doesn't require any particular machine** &mdash; it can run on a
laptop, an SCC node, anything with `pip` &mdash; because it always resolves wheels
for tiCrypt's exact target (Python version, ABI, platform) via `pip download`'s
cross-platform flags, rather than relying on the download machine's own
environment. See [`plan.md`](plan.md) for the environment discovery behind
those target values.

## Two workflows

**[`ticrypt/`](ticrypt/)** — researcher wishlist. You know the specific packages you
want (e.g. `requests`, `pandas`); `ticrypt_packages.py` downloads just those plus
their dependencies (pip resolves the closure itself) and installs them into tiCrypt.
This is almost certainly the one you want day-to-day — see
[`ticrypt/README.md`](ticrypt/README.md).

**[`install_packages/`](install_packages/)** — full environment replication. Freezes
*everything currently installed* on one machine (`list_packages.py` &rarr;
`requirements.txt`) and reproduces that whole set on another. Useful for cloning an
entire existing environment, not for adding a few packages.

## Usage (`ticrypt/`, the common case)

On any internet-connected machine:

```bash
python3 ticrypt/ticrypt_packages.py download requests pandas numpy
```

Copy the resulting `ticrypt_packages/` folder to tiCrypt, then on tiCrypt:

```bash
module load python3/3.13.8
python3 ticrypt_packages/ticrypt_packages.py install
```

## Usage (`install_packages/`, full env replication)

On the machine whose packages you want to replicate:

```bash
python3 install_packages/list_packages.py requirements.txt
```

On any internet-connected machine:

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
