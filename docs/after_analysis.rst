After the analysis: reading results
====================================

Open a completed rigorous analysis once, then use the returned ``AnalysisInfo``
to inspect its result. The examples below assume ``analysis_folder`` points to
an existing analysis directory and that its input data are available.

.. code-block:: python

   import molass

   info = molass.load_analysis(analysis_folder)
   result = info.result
   print(info.describe())

If no completed job exists yet, ``info.result`` is ``None``. ``info.summary()``
reports the analysis status and ``info.diagnose()`` reports file-based warnings.

Elution curves and moments
--------------------------

``result.xr_icurve`` is the measured total XR elution curve;
``result.xr_ccurves`` contains the component curves. ``get_moment()``
returns a moment object whose ``get_meanstd()`` gives the mean frame and
standard deviation.

.. code-block:: python

   total_mean, total_std = result.xr_icurve.get_moment().get_meanstd()
   component_moments = [
       curve.get_moment().get_meanstd()
       for curve in result.xr_ccurves
   ]

Data and model Rg curves
------------------------

The data curve fits each measured frame. The model curve reconstructs Rg from
the optimized component Rg values and elution profiles.

.. code-block:: python

   data_rg = info.decomp.get_rg_curve()
   model_rg = result.compute_reconstructed_rgcurve()
   reliable_frames, reliable_rgs = data_rg.reliable()

Component profiles and Guinier fits
-----------------------------------

``get_xr_matrices()`` returns ``M, C, P, Pe``. Each column of ``P`` is one
component's scattering profile over ``result.xr.qv``. Component objects also
provide their Guinier fit and profile data.

.. code-block:: python

   M, C, P, Pe = result.get_xr_matrices()
   q = result.xr.qv
   component_guinier = [
       component.get_guinier_object()
       for component in result.get_xr_components()
   ]

Kratky shape match
------------------

The shape match compares the component profiles with the library's reference
shapes. Its result exposes the score matrices and can be serialized directly.

.. code-block:: python

   shape_match = result.get_kratky_shape_match()
   first_component_best_shape = shape_match.best_shape(0)
   saved_shape_match = shape_match.to_dict()

Distinct species or slices of a continuum?
------------------------------------------

The continuity report asks whether the data support a few *distinct species*.
A single species has the same Rg at every concentration, so a mixture of
distinct species shows plateaus in the per-frame Rg curve of the data, whereas
a continuum shows a ramp. The report combines this plateau test with the shape
heterogeneity of the component Kratky curves and the ordering of the
components along the elution (from four components).

.. code-block:: python

   report = result.get_continuity_report()
   print(report)
   report.verdict, report.power, report.excess, report.plateaus
   report.plot()                         # (a) data Rg, plateaus, component Rg; (b) Kratky plots
   report.to_dict()                      # JSON-serializable

The report takes seconds: it needs the Rg curve and the component Kratky curves, not the
reference-shape library. ``get_continuity_report(shapes=True)`` also lists the best library shape of
each component (the library is built once, about 30 s, and cached on disk). The building blocks are
public: ``result.get_reliable_rg()`` (frames and Rg of the reliable points), ``result.get_kratky_curves()``,
``result.get_component_extents()`` and ``result.get_rg_curve().noise()`` / ``.drop()``.

The verdict is ``"discrete"``, ``"no evidence for distinct species"`` or
``"undetermined"``; it is never "continuum", because a continuum can only be
*not excluded*. Read it together with its regime:

* ``"discrete"`` is the reliable finding: it needs clear plateaus
  (``excess`` of at least 2) in an Rg curve that drops by at least 5 noise units.
* ``"no evidence ..."`` is weak evidence at best. With a small Rg drop against
  the noise (``power`` below about 20) a staircase still looks like a ramp, and
  the report says so in ``notes``.
* The Kratky ``max_separation`` measures how different the component *shapes*
  are, not discreteness: a wide continuum differs as much as discrete species
  of different shapes, and two compact proteins look alike. It is reported, not
  used for the verdict.
* The thresholds are heuristics calibrated on a few real analyses and on
  simulations with known truth (molass-researcher, experiments 51i-51r); they
  can be overridden, e.g. ``result.get_continuity_report(excess_min=2.5)``.
  The array-level indicators (``molass.Continuity.plateau_excess``,
  ``find_plateaus``, ``kratky_separation``) can be used on their own.

Decomposition residual
----------------------

The LRF residual is the relative Frobenius-norm reconstruction error
``||M - PC|| / ||M||``.

.. code-block:: python

   residual = result.get_lrf_residual()

Quiet and repeatable runs (scripts, agents, headless)
-----------------------------------------------------

.. code-block:: python

   import molass
   molass.set_progress(False)            # no progress bars (or the environment variable MOLASS_PROGRESS=0);
                                         # by default they are shown only in a terminal or a notebook
   molass.set_cache_dir("C:/cache")      # opt-in: reuse per-frame Rg curves of the same data in later
                                         # processes (or MOLASS_CACHE_DIR); keyed by data and trimming
   molass.version_info()                 # the version in use, where it comes from, and whether the
                                         # installed metadata (pip) agrees with the code

Concentration-free mass of components and frames
------------------------------------------------

The volume of correlation :math:`V_c = I(0) / \int q\,I(q)\,dq` of a profile gives a mass without a
concentration and without :math:`D_{max}` (Rambo and Tainer 2013; the integral runs to :math:`q = 0.3`, as in the ATSAS
program DATVC). It is a calibration on proteins and comes out low: on 11 SASBDB protein entries of 13.7-479 kDa it is
0.77-0.95 of the sequence mass (median 0.83), the same as DATVC. It is not meant for other particles. Like the Porod
volume it follows :math:`R_g` along the elution for species of equal mass whose conformation changes, so a mass curve
cannot tell a conformational continuum from species of different size.

.. code-block:: python

   corrected = ssd.trimmed_copy().corrected_copy()
   decomp = corrected.quick_decomposition(num_components=3, rgcurve=corrected.get_rg_curve(), proportions=[1]*3)
   for comp in decomp.get_xr_components():
       m = comp.get_volume_mass()          # VolumeMass: .mass (kDa), .vc (A^2), .qr, .q_cut, .reason if NaN
       print(f"{m.mass:.1f} kDa (Vc {m.vc:.0f} A^2, q cut {m.q_cut:.3f})")

   curve = corrected.get_volume_mass_curve()   # per frame, next to get_rg_curve(); curve.plot() draws mass and Rg

See :mod:`molass.SAXS.VolumeMass` for the formula and its limits.
Freeze a compact JSON summary
-----------------------------

The default summary contains the recipe, job history and per-component
metadata. Derived curves, Kratky profiles and Rg curves are opt-in because
they may require additional computation.

.. code-block:: python

   summary_path = info.freeze(
       "analysis-summary.json",
       include=("curves", "kratky", "rgcurve"),
   )

For an in-process accessor list, use ``info.describe()``. For field-level
details, see the API reference for :class:`~molass.DataObjects.Curve.Curve`,
:class:`~molass.Guinier.RgCurve.RgCurve`, and
:class:`~molass.LowRank.Decomposition.Decomposition`.
