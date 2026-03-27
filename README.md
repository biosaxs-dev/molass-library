<h1 align="center"><a href="https://biosaxs-dev.github.io/molass-library"><img src="docs/_static/molass-title.png" width="300"></a></h1>

Molass Library is a rewrite of [MOLASS](https://pfwww.kek.jp/saxs/MOLASSE.html), a tool for the analysis of SEC-SAXS experiment data currently hosted at the Japanese synchrotron radiation facilities, [Photon Factory](https://pfwww.kek.jp/saxs/MOLASS.html) and [SPring-8](https://www.riken.jp/en/research/labs/rsc/rd_ts_sra/life_sci_res_infrastruct/index.html)

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

- **Beginner Onboarding:** https://github.com/biosaxs-dev/molass-beginner — Agent-mode first-run guide, for first-time users
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

Context is auto-loaded from `.github/copilot-instructions.md` when using GitHub Copilot in Agent mode (AI Context Standard v0.7).

For behavioral rules and user-type guidance, see [`Copilot/copilot-guidelines.md`](https://github.com/biosaxs-dev/molass-library/blob/master/Copilot/copilot-guidelines.md).

## Optional Features

**Excel reporting (Windows only):**

If you want to use Excel reporting features (Windows only) for backward compatibility, install with the `excel` extra:

```
pip install -U molass[excel]
```

> **Note:** The `excel` extra installs `pywin32`, which is required for Excel reporting and only works on Windows.

