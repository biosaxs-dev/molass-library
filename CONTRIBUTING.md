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
```

## Reporting issues

Please use the [GitHub issue tracker](https://github.com/biosaxs-dev/molass-library/issues).

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
