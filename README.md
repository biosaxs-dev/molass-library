<h1 align="center"><a href="https://biosaxs-dev.github.io/molass-library"><img src="docs/_static/molass-title.png" width="300"></a></h1>

Molass Library is a rewrite of [MOLASS](https://pfwww.kek.jp/saxs/MOLASSE.html), a tool for the analysis of SEC-SAXS experiment data currently hosted at [Photon Factory](https://www2.kek.jp/imss/pf/eng/) and [SPring-8](http://www.spring8.or.jp/en/), Japan.

## Tested Platforms

- Python 3.13 on Windows 11
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

Especially for testing, see the first two sections in
- **Testing:** https://biosaxs-dev.github.io/molass-develop/chapters/06/testing.html

## Copilot Usage

Before starting a Copilot chat session with this repository, please use the following magic phrase to ensure Copilot follows project rules:
For details on Copilot rules and usage, see [`Copilot/copilot-guidelines.md`](https://github.com/biosaxs-dev/molass-library/blob/master/Copilot/copilot-guidelines.md).

> “Please follow the Copilot guidelines in this project for all advice and responses.”

## Optional Features

**Excel reporting (Windows only):**

If you want to use Excel reporting features (Windows only) for backward compatibility, install with the `excel` extra:

```
pip install -U molass[excel]
```

> **Note:** The `excel` extra installs `pywin32`, which is required for Excel reporting and only works on Windows.

