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

Decomposition residual
----------------------

The LRF residual is the relative Frobenius-norm reconstruction error
``||M - PC|| / ||M||``.

.. code-block:: python

   residual = result.get_lrf_residual()

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
