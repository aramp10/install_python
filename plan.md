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

1. **Python version** — use the `python3/3.13.8` module on both sides. Exact
   version match (`cpython-313`) removes any need for `--python-version`/`--abi`
   flags on `pip download`.
2. **Conda or pip** — pure pip/module system on both machines. No `conda-pack`
   workflow needed.
3. **Same or different platform** — same CPU arch (x86_64) and same CPython
   build, but different OS major version: `scc-yd2` is el8 (glibc 2.28),
   tiCrypt is el9 (glibc 2.34). This is not a blocker: manylinux wheels are
   glibc-forward-compatible, so wheels resolved as compatible with el8's older
   glibc will also load on el9's newer glibc. `pip download` can run on
   `scc-yd2` with `python3/3.13.8` loaded and **no manual `--platform`/`--abi`
   flags** — but since SCC nodes vary, re-verify OS/arch if the download step
   ends up running on a different node.
4. **Compiler on tiCrypt** — yes, GCC 11.5.0, so source builds work as a
   fallback if a package has no wheel. (`scc-yd2` has the older GCC 8.5.0, but
   that only affects the download side if source dists get built there too.)
