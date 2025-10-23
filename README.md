<h1 align="center"><a href="https://biosaxs-dev.github.io/molass-library"><img src="docs/_static/molass-title.png" width="300"></a></h1>

Molass Library is a rewrite of [MOLASS](https://pfwww.kek.jp/saxs/MOLASSE.html), a tool for the analysis of SEC-SAXS experiment data currently hosted at [Photon Factory](https://www2.kek.jp/imss/pf/eng/) and [SPring-8](http://www.spring8.or.jp/en/), Japan.

## Tested Platforms

- Python 3.12 on Windows 11
- Python 3.12 on Ubuntu 22.04.4 LTS (WSL2)

## Installation

To install this package, use pip as follows:

```
pip install -U molass
```

## Documentation

- **Tutorial:** https://biosaxs-dev.github.io/molass-tutorial — practical usage, for beginners
- **Essence:** https://biosaxs-dev.github.io/molass-essence — theory, for researchers
- **Technical Report:** https://biosaxs-dev.github.io/molass-technical — technical details, for advanced users
- **Reference:** https://biosaxs-dev.github.io/molass-library — function reference, for coding
- **Legacy Repository:** https://github.com/biosaxs-dev/molass-legacy — legacy code

## Community

To join the community, see:

- **Handbook:** https://biosaxs-dev.github.io/molass-develop — maintenance, for developers

## Optional Features

**Excel reporting (Windows only):**

If you want to use Excel reporting features (Windows only) for backward compatibility, install with the `excel` extra:

```
pip install -U molass[excel]
```

> **Note:** The `excel` extra installs `pywin32`, which is required for Excel reporting and only works on Windows.

For testing and development, install with the `testing` extra to get additional pytest plugins:

```
pip install -U molass[testing]
```

> **Note:** The `testing` extra installs `pytest-env` and `pytest-order` for enhanced test execution control.

You can also combine extras as needed:

```
pip install -U molass[excel,testing]
```