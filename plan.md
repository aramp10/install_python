# Installing Python Packages on an Air-Gapped System (tiCrypt)

The `install_r/` repo uses a **download → transfer → offline-install** pattern.
Python's `pip` has native support for the same approach.

## Analogous workflow

| R step | Python equivalent |
|---|---|
| `Rscript list_packages.R` | `pip freeze > requirements.txt` |
| `Rscript install_packages.R download` | `pip download -r requirements.txt -d DIST/` |
| Copy `DIST/` to target | Copy `DIST/` to tiCrypt |
| `Rscript install_packages.R offline` | `pip install --no-index --find-links=DIST -r requirements.txt` |

---

## Key complication: platform-specific wheels

R downloads source tarballs that compile on the target. Python wheels are pre-compiled
and **platform-specific** (OS, CPU arch, Python version, ABI). If the download machine
differs from tiCrypt, you must tell `pip download` what the target looks like:

```bash
pip download \
  --dest DIST/ \
  --platform linux_x86_64 \
  --python-version 3.11 \
  --implementation cp \
  --abi cp311 \
  --only-binary=:all: \
  -r requirements.txt
```

If no wheel exists for a package, `--only-binary=:all:` will fail that package. Drop
the flag to allow source distributions, but then the target needs a compatible compiler
(same situation as R's source tarballs).

---

## Proposed scripts (three files, mirroring `install_packages/`)

**`list_packages.py`** — dumps the current environment's packages to `requirements.txt`
- Wraps `pip freeze` (or `importlib.metadata`) to exclude base/stdlib packages
- Produces the input list for the download step

**`install_packages.py [mode] [requirements.txt]`** — three modes:

- **`download`** — calls `pip download` into `DIST/`, resolving the full dependency
  closure for the target platform
- **`offline`** — calls `pip install --no-index --find-links=DIST` from the local
  folder; no network access
- **`online`** — calls `pip install -r requirements.txt` from PyPI (for the
  internet-connected side)

Environment knobs (mirroring the R knobs):

| Variable | Effect |
|---|---|
| `DIST_DIR` | Location of the download folder (default `./DIST`) |
| `PYPI_REPO` | PyPI mirror URL for download mode |
| `TARGET_PYTHON_VERSION` | Python version on tiCrypt (e.g. `3.11`) |
| `TARGET_PLATFORM` | Wheel platform tag (e.g. `linux_x86_64`) |
| `TARGET_ABI` | ABI tag (e.g. `cp311`) |

---

## Environment discovery (answered 2026-07-10)

Two systems are involved: **tiCrypt** (the air-gapped target, accessed via its
web-based terminal hub) and a **BU SCC compute node** (the internet-connected
machine where `pip download` will run). Note: BU SCC is a heterogeneous
cluster — different compute nodes can have different OS versions, so the
findings below are specific to the node used (`scc-yd2`) and should be
re-checked if a different node is used for the download step.

### tiCrypt VM (target)

Commands run in the tiCrypt web terminal:

```bash
which python python3
module avail python3

/usr/bin/python3 --version
/usr/bin/python3 -c "import sysconfig; print(sysconfig.get_platform())"

module load python3/3.13.8
which python3
python3 --version
python3 -c "import sys; print(sys.prefix)"
python3 -c "import sysconfig; print(sysconfig.get_platform())"
python3 -c "import sys; print(sys.implementation.cache_tag)"
python3 -m pip --version

which conda mamba 2>/dev/null
module avail conda 2>/dev/null
module avail anaconda 2>/dev/null
echo $CONDA_DEFAULT_ENV
echo $VIRTUAL_ENV

which gcc g++ cc make
gcc --version

cat /etc/os-release
```

Findings:

| Item | Value |
|---|---|
| OS | AlmaLinux 9.7 (el9) |
| Arch | x86_64 |
| System `/usr/bin/python3` | 3.9.25 (not used) |
| Module `python3/3.13.8` | **target Python** — pip 25.2, `cpython-313`, `linux-x86_64` |
| Conda/mamba | none available — pure pip |
| Compiler | GCC 11.5.0 (Red Hat 11.5.0-11), g++/cc/make present |

### BU SCC compute node (download machine)

Hostname: **`scc-yd2`**. Commands run directly on the compute node:

```bash
hostname
cat /etc/os-release
uname -m

module avail python3 2>&1 | grep -i python3
which gcc g++
gcc --version

module load python3/3.13.8
which python3
python3 --version
python3 -c "import sysconfig; print(sysconfig.get_platform())"
python3 -c "import sys; print(sys.implementation.cache_tag)"
python3 -m pip --version
```

Findings:

| Item | Value |
|---|---|
| Hostname | `scc-yd2` |
| OS | AlmaLinux 8.10 (el8) |
| Arch | x86_64 |
| Module `python3/3.13.8` | available, marked as default (`D`) — pip 25.2, `cpython-313`, `linux-x86_64` |
| Conda/mamba | not checked (not needed — matches tiCrypt's pure-pip setup) |
| Compiler | GCC 8.5.0 (Red Hat 8.5.0-28) |

### Conclusions

1. **Python version** — tiCrypt uses the `python3/3.13.8` module.
2. **Conda or pip** — pure pip/module system on both machines. No `conda-pack`
   workflow needed.
3. **Same or different platform** — `scc-yd2` (el8, glibc 2.28) and tiCrypt
   (el9, glibc 2.34) happen to be close enough that no cross-platform flags
   would strictly be *required* if the download always ran on a matching SCC
   node. See the revised decision below — that assumption was dropped.
4. **Compiler on tiCrypt** — yes, GCC 11.5.0, so source builds work as a
   fallback if a package has no wheel.

### Revised decision (2026-07-10, after team meeting)

The download machine is **not assumed to be any particular machine** — it could
be a personal laptop (any OS/arch), not necessarily an SCC node. This rules out
the "load the same `python3/3.13.8` module on both sides" shortcut above, since
there's no guarantee the download machine can load that module at all.

Instead, `pip download` always resolves wheels for **tiCrypt's target**
explicitly, via `--python-version`, `--implementation`, `--abi`, and
`--platform` flags — regardless of what machine or Python version is actually
running the download. This is the original "Key complication" approach from
the top of this file, now the primary path rather than a fallback.

Target constants (hardcoded in `ticrypt/ticrypt_packages.py`, derived from the
environment discovery above):

| Flag | Value | Why |
|---|---|---|
| `--python-version` | `3.13` | tiCrypt's `python3/3.13.8` module |
| `--implementation` | `cp` | CPython |
| `--abi` | `cp313` | matches Python 3.13's `cache_tag` |
| `--platform` (repeated) | `manylinux2014_x86_64`, `manylinux_2_17_x86_64`, `manylinux_2_28_x86_64`, `linux_x86_64` | tiCrypt is x86_64 with glibc 2.34 (AlmaLinux 9.7); listing older manylinux baselines too maximizes wheel coverage, since manylinux tags are glibc-forward-compatible and many wheels only publish older tags |

`--only-binary=:all:` is the default (wheels only, since cross-platform
resolution can't build from source for a machine other than the one running
pip); an `--allow-sdist` opt-in exists for packages without a matching wheel,
relying on tiCrypt's own GCC 11.5.0 to build them during the offline install
step.

Verified end-to-end on 2026-07-10: `ticrypt_packages.py download pandas
matplotlib` from a machine running Python 3.13/AlmaLinux 8, targeting the
constants above, correctly resolved and fetched pure-wheel builds (including
transitive deps) for `cp313`/`manylinux_2_28_x86_64` — several wheels (pandas,
numpy, pillow, contourpy) only matched because `manylinux_2_28_x86_64` was in
the platform list, confirming it's load-bearing, not just precautionary. The
downloaded folder installed offline via `--no-index --find-links` into a
fresh venv and imported successfully.
