---
title: 'Molass Library: A Python Package for SEC-SAXS Data Analysis'
tags:
  - Python
  - SEC-SAXS
  - Bio-SAXS
authors:
  - name: Masatsuyo Takahashi
    orcid: 0009-0007-1466-5563
    corresponding: false    
    affiliation: "1"
  - name: Nobutaka Shimizu
    orcid: 0000-0002-3636-1663
    corresponding: true
    affiliation: "1,2"
affiliations:
  - name: Structural Biology Research Center, Institute of Materials Structure Science, High Energy Accelerator Research Organization (KEK)
    index: 1
  - name: Photon Factory, Institute of Materials Structure Science, High Energy Accelerator Research Organization (KEK)
    index: 2
    ror: 0327y7e25
  - name: Life Science Research Infrastructure Group, RIKEN SPring-8 Center
    index: 3
    ror: 01sjwvz98
date: 24 March 2025
bibliography: paper.bib

---

# Summary

The **Molass Library** is a modern, open-source Python package for the analysis of SEC-SAXS (Size Exclusion Chromatography coupled with Small Angle X-ray Scattering) experimental data. It is a comprehensive rewrite of the original MOLASS tool [@Yonezawa:2023], currently hosted at [Photon Factory](https://pfwww.kek.jp/saxs/MOLASS.html) and [SPring-8](https://www.riken.jp/en/research/labs/rsc/rd_ts_sra/life_sci_res_infrastruct/index.html), Japan. By leveraging the Python ecosystem and supporting scripting in Jupyter notebooks [@Kluyver:2016aa], Molass Library offers greater flexibility, reproducibility, and extensibility compared to its predecessor.

A typical SEC-SAXS experiment involves two distinct yet interdependent processes:

* **SEC** – Size Exclusion Chromatography
* **SAXS** – Small Angle X-ray Scattering

Effective analysis requires integrating both domains, which the Molass Library facilitates through a unified, scriptable workflow.

![Logo of Molass Library designed by K. Yatabe](docs/_static/molass_256.png)

# Statement of Need

Analysis of SEC-SAXS data is inherently multi-step and complex. A standard workflow includes:

1. Circular Averaging
2. Background Subtraction
3. Trimming
4. Baseline Correction
5. Low Rank Factorization
6. Radius of Gyration (Rg) Estimation – Guinier Plot [@Guinier_1939]
7. Shape Inspection – Kratky Plot [@Kratky_1963]
8. Electron Density Estimation

The Molass Library currently implements steps 3–7. For steps 1 and 2, users may employ SAngler [@Shimizu:2016], and for step 8, DENSS [@Grant:2018] is recommended. While alternative tools exist—such as the proprietary ATSAS suite [@Manalastas-Cantos:ge5081] and the open-source BioXTAS RAW [@Hopkins:jl5075]—Molass Library distinguishes itself by providing an open, scriptable, and modular platform, empowering researchers to customize and extend their analysis pipelines within the Python ecosystem.

# Key Features and Dependencies

Molass Library is built on robust scientific Python libraries, including NumPy [@Harris2020], SciPy [@Virtanen2020], and Matplotlib [@Hunter:2007]. It further integrates:

* **pybaselines** [@pybaselines] for advanced baseline correction
* **ruptures** [@TRUONG2020107299] for change point detection
* **scipy.signal.find_peaks** for peak recognition

By adopting these well-maintained packages, Molass Library reduces custom code and enhances reliability. The transition from a GUI-based workflow (previously using Tkinter [@lundh1999introduction]) to Jupyter-based scripting further streamlines reproducibility and collaboration.

# Theoretical Foundation

A central feature of Molass Library is **low rank factorization** using elution curve models, enabling decomposition of overlapping chromatographic peaks—a common challenge in SEC-SAXS analysis. The decomposition is formulated as:

$$ M = P \cdot C \qquad (1) $$

where:

* $M$: measured data matrix
* $P$: matrix of component scattering curves
* $C$: matrix of component elution curves

The optimal solution (in the least-squares sense) is:

$$ P = M \cdot C^{+} \qquad (2) $$

where $C^{+}$ denotes the Moore-Penrose pseudoinverse [@Penrose_1955; @Penrose_1956]. This approach enables robust separation of components, even in the presence of overlapping peaks, provided suitable constraints are applied.

![Illustration of Decomposition using Simulated Data](docs/_static/simulated_data.png)

# Elution Curve Modeling

To address underdeterminedness and improve interpretability, Molass Library incorporates several elution curve models:

* **EGH**: Exponential Gaussian Hybrid [@LAN20011]
* **SDM**: Stochastic Dispersive Model [@Felinger1999]
* **EDM**: Equilibrium Dispersive Model [@Ur2021]

These models allow users to impose domain-specific constraints, enhancing the accuracy and physical relevance of the decomposition. The library also supports model-free approaches, such as REGALS [@Meisburger:mf5050], for comparison.

# Availability and Documentation

Molass Library is freely available under an open-source license at [https://github.com/freesemt/molass-library](https://github.com/freesemt/molass-library). Comprehensive documentation, including tutorials and theoretical background, is provided at [Molass Essence](https://freesemt.github.io/molass-essence/chapters/04/lowrank.html).

# Acknowledgements

This research was partially supported by the Platform Project for Supporting Drug Discovery and Life Science Research [Basis for Supporting Innovative Drug Discovery and Life Science Research (BINDS)] from AMED under grant numbers ... ...

# References

