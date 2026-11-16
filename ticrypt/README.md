# Installing Python packages in tiCrypt

tiCrypt has no internet access, so you can't `pip install` there directly.
`ticrypt_packages.py` lets you fetch the packages you want (and everything they
depend on) on an internet-connected machine, carry them into tiCrypt as one folder,
and install them.

## Step 1 — On an internet-connected machine (an SCC node, ...)

Load the **same Python module tiCrypt uses** before downloading — this is what lets
the downloaded wheels work on tiCrypt without extra platform flags (see
[`../plan.md`](../plan.md)):

```bash
module load python3/3.13.8
python3 ticrypt_packages.py download pyfaidx
```

This creates a folder named `ticrypt_packages/` containing:
- the **wheels/sdists** for the packages you asked for, plus all their dependencies
  (pip resolves the closure itself),
- a copy of `ticrypt_packages.py` itself (so the folder is self-contained),
- `REQUESTED.txt` (the packages you asked for) and `TICRYPT_TARGET.json` (the Python
  version/platform the download was resolved under).

If you're on a machine running the wrong Python version, `download` stops immediately
and tells you which module to load.

## Step 2 — Copy the folder into tiCrypt

Move the whole `ticrypt_packages/` folder into tiCrypt using your normal transfer
method. Then delete the copy on your local computer.

## Step 3 — Inside tiCrypt, install

Create and activate a virtual environment first, then install into it — this keeps
packages isolated in your own venv rather than landing in your home directory's user
site-packages:

```bash
module load python3/3.13.8
virtualenv ~/venvs/my_venv
source ~/venvs/my_venv/bin/activate
python3 ticrypt_packages/ticrypt_packages.py install
```

Packages install with `pip install --no-index --find-links=...`, no network access.

You'll need to reload the module and reactivate the venv (`source
~/venvs/my_venv/bin/activate`) at the start of each new tiCrypt session before using
these packages again.

Before installing, `install` checks that this system's Python version/platform match
what the folder was downloaded for. If they don't match it **stops** and explains the
mismatch (unless you pass `--force`) — re-run `download` on a machine matching
tiCrypt's Python module and copy the folder over again.

## Step 4 — Verify

Confirm the package actually installed and is importable:

```bash
python3 -c "import pyfaidx; print(pyfaidx.__version__)"
```

If a package was already present in tiCrypt's Python module, `install` will print
"Requirement already satisfied" instead of actually installing from the downloaded
wheels — this check confirms which case you're in.

## Options

- **Different folder name:** `download ... --dir my_pkgs` then `install --dir my_pkgs`.
- **Alternate index:** `download ... --index-url https://...` (e.g. an internal PyPI
  mirror).
- **Install despite a version/platform mismatch:** `install --force`.

## Notes for RCS / admins

`TICRYPT_PYTHON_VERSION` at the top of `ticrypt_packages.py` is the major.minor
Python version tiCrypt's module provides. **Update it when tiCrypt's `python3` module
changes** — `download` checks the *running* interpreter against this constant and
refuses to proceed on a mismatch, since (unlike the R version of this tool, which
forces dependency resolution against an explicit target R/OS regardless of what's
running) this workflow relies on the download machine already running a Python that
matches tiCrypt, rather than forcing cross-platform resolution via pip's
`--python-version`/`--platform`/`--abi` flags.

This tool is a researcher-friendly distillation of the admin workflow in
[`../install_packages/`](../install_packages/) (`download` → `offline`), scoped to a
short wishlist of packages instead of a whole environment.
