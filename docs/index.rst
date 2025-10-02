.. molass documentation master file, created by
   sphinx-quickstart on Fri Mar 14 07:21:52 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Molass Library Reference
========================

Molass Library is a rewrite of `MOLASS <https://pfwww.kek.jp/saxs/MOLASSE.html>`_, a tool for the analysis of SEC-SAXS experiment data currently hosted at `Photon Factory <https://www2.kek.jp/imss/pf/eng/>`_ and `SPring-8 <http://www.spring8.or.jp/en/>`_, Japan.

This document describes each function of the library.

For more structural information, see also:

- **Tutorial:** https://molass-saxs.github.io/molass-tutorial on practical usage, for beginners
- **Essence:** https://molass-saxs.github.io/molass-essence on theory, for researchers
- **Technical Report:** https://freesemt.github.io/molass-technical/ on technical details, for advanced users
- **Legacy Reference:** https://freesemt.github.io/molass-legacy/ for function reference of the GUI application version, the predecessor.

To join the community, see also:

- **Handbook:** https://molass-saxs.github.io/molass-develop on maintenance, for developers.

Module Functions
----------------

.. automodule:: molass
   :members:
   :undoc-members:
   :show-inheritance:

Submodules
----------

.. toctree::
   :maxdepth: 5

   source/molass.Baseline
   source/molass.Bridge
   source/molass.DataObjects
   source/molass.DataUtils
   source/molass.Decompose
   source/molass.DensitySpace
   source/molass.Except
   source/molass.FlowChange
   source/molass.Global
   source/molass.Guinier
   source/molass.InterParticle
   source/molass.Legacy
   source/molass.Local
   source/molass.LowRank
   source/molass.Mapping
   source/molass.PackageUtils
   source/molass.Peaks
   source/molass.PlotUtils
   source/molass.Progress
   source/molass.Reports
   source/molass.SAXS
   source/molass.SAXS.Models
   source/molass.SEC
   source/molass.SEC.Models
   source/molass.Shapes
   source/molass.Stats
   source/molass.SurveyUtils
   source/molass.Trimming

Tool Functions
----------------

.. toctree::
   :maxdepth: 5

   source/EditRst