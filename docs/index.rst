.. molass documentation master file, created by
   sphinx-quickstart on Fri Mar 14 07:21:52 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Molass Library Reference
========================

Molass Library is a rewrite of `MOLASS <https://pfwww.kek.jp/saxs/MOLASSE.html>`_, an analytical tool for SEC-SAXS experiment data currently hosted at `Photon Factory <https://www2.kek.jp/imss/pf/eng/>`_ or `SPring-8 <http://www.spring8.or.jp/en/>`_, Japan.

This document describes each function of the library.

For details, see also:

- **Essence:** https://nshimizu0721.github.io/molass-essence for theory,
- **Tutorial:** https://nshimizu0721.github.io/molass-tutorial for how to use,
- **Technical Report:** https://freesemt.github.io/molass-technical/ for technical details,
- **Legacy Reference:** https://freesemt.github.io/molass-legacy/ for the GUI application version.

To join the community, see also:

- **Handbook:** https://nshimizu0721.github.io/molass-develop for maintenance.

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
   source/molass.CurveModels
   source/molass.CurveModels.Scattering
   source/molass.CurveModels.Scattering.FormFactors
   source/molass.DataObjects
   source/molass.DataUtils
   source/molass.DensitySpace
   source/molass.DENSS
   source/molass.Except
   source/molass.FlowChange
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
   source/molass.Shapes
   source/molass.Stats
   source/molass.Stochastic
   source/molass.SurveyUtils
   source/molass.Trimming

Tool Functions
----------------

.. toctree::
   :maxdepth: 5

   source/EditRst
   source/UsualUpdate