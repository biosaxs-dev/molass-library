<h1 align="center"><a href="https://biosaxs-dev.github.io/molass-library"><img src="docs/_static/molass-title.png" width="300"></a></h1>

Molass Library is a rewrite of [MOLASS](https://pfwww.kek.jp/saxs/MOLASSE.html), a tool for the analysis of SEC-SAXS experiment data currently hosted at [Photon Factory](https://www2.kek.jp/imss/pf/eng/) and [SPring-8](http://www.spring8.or.jp/en/), Japan.

To install this package, use pip as follows.

```
pip install -U molass
```

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

For more information, see:

- **Tutorial:** https://biosaxs-dev.github.io/molass-tutorial — on practical usage, for beginners
- **Essence:** https://biosaxs-dev.github.io/molass-essence — on theory, for researchers
- **Technical Report:** https://freesemt.github.io/molass-technical — on technical details, for advanced users
- **Reference:** https://biosaxs-dev.github.io/molass-library — on function reference, for coding
- **Legacy Repository:** https://github.com/freesemt/molass-legacy — for legacy code

To join the community, see also:

- **Handbook:** https://biosaxs-dev.github.io/molass-develop on maintenance, for developers.

<br>