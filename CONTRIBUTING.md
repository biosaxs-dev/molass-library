# Contributing to Molass Library

Thank you for your interest in contributing!

## Developer Handbook

Full contribution guidance — including environment setup, coding conventions, and the PR workflow — is in the **[Molass Developer's Handbook](https://biosaxs-dev.github.io/molass-develop)**.

The most relevant sections for new contributors are:

- [Setting up a development environment](https://biosaxs-dev.github.io/molass-develop/chapters/06/testing.html)
- [Running the test suite](https://biosaxs-dev.github.io/molass-develop/chapters/06/testing.html)

## Quick start

```bash
# 1. Clone both repos as siblings
git clone https://github.com/biosaxs-dev/molass-library
git clone https://github.com/biosaxs-dev/molass-legacy

# 2. Install molass with testing extras
cd molass-library
pip install -e ".[testing]"
pip install molass_data

# 3. Run the tutorial tests
pytest tests/tutorial/ -v

# 4. Run the fast generic tests (seconds to minutes, no local data; CI runs this on every push)
pytest tests/generic -m fast

# 5. Before a release: the full suite (about 40 minutes; needs the local data sets, so run it on the
#    maintainer's machine; tests without data are skipped)
pytest tests/tutorial tests/generic
```

A test module of `tests/generic` that runs in seconds without local data is added to the `fast` subset
in `tests/generic/conftest.py`.

## Reporting issues

Please use the [GitHub issue tracker](https://github.com/biosaxs-dev/molass-library/issues).

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
