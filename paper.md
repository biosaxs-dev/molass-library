---
title: 'Molass Library: A Python Package for SEC-SAXS Data Analysis'
tags:
  - Python
  - SEC-SAXS
  - BioSAXS
authors:
  - name: Masatsuyo Takahashi
    orcid: 0009-0007-1466-5563
    corresponding: false    
    affiliation: "1"
  - name: Nobutaka Shimizu
    orcid: 0000-0002-3636-1663
    corresponding: true
    affiliation: "1,2,3"
affiliations:
  - name: Structural Biology Research Center, Institute of Materials Structure Science, High Energy Accelerator Research Organization (KEK)
    index: 1
  - name: Photon Factory, Institute of Materials Structure Science, High Energy Accelerator Research Organization (KEK)
    index: 2
  - name: Life Science Research Infrastructure Group, R&D of Technology and Systems for Synchrotron Radiation Applications Division, RIKEN SPring-8 Center
    index: 3
    ror: 01d1kv753
date: 2 October 2025
bibliography: paper.bib

---

# Summary

Molass Library is a modern, open-source Python package designed for the analysis of SEC-SAXS (Small-Angle X-ray Scattering coupled with Size Exclusion Chromatography) experimental data. It represents a comprehensive rewrite of the original MOLASS tool [@Yonezawa:2023], currently hosted at the Japanese synchrotron radiation facilities, [Photon Factory](https://pfwww.kek.jp/saxs/MOLASS.html) and [SPring-8](https://www.riken.jp/en/research/labs/rsc/rd_ts_sra/life_sci_res_infrastruct/index.html). By leveraging the Python ecosystem and supporting interactive scripting in Jupyter notebooks, Molass Library provides enhanced flexibility, reproducibility, and extensibility compared to its predecessor.

A typical SEC-SAXS experiment involves two interconnected processes:

* **SEC** – Size Exclusion Chromatography
* **SAXS** – Small-Angle X-ray Scattering

Effective analysis requires seamless integration of both domains, which Molass Library facilitates through a unified, scriptable workflow.

![Logo of Molass Library designed by K. Yatabe](docs/_static/molass_256.png)

# Statement of Need

Analysis of SEC-SAXS data is inherently multi-step and complex. A typical workflow includes:

1. Circular (Azimuthal) averaging
2. Background subtraction
3. Trimming of data
4. Baseline correction
5. Low rank factorization
6. Radius of gyration (*R*~g~) estimation – Guinier plot [@Guinier_1939]
7. Folding state estimation – Kratky plot [@Kratky_1963]
8. Electron density calculation 

Molass Library currently implements steps 3–7. For steps 1 and 2, users may employ SAngler [@Shimizu:2016] or device-specific software, while for step 8, DENSS [@Grant:2018] is recommended. Although alternative tools exist, such as the proprietary program suite ATSAS [@Manalastas-Cantos:ge5081] and the open-source program BioXTAS RAW [@Hopkins:jl5075], Molass Library distinguishes itself by providing an open, scriptable, and modular platform. This design empowers researchers to flexibly tailor and extend their analysis pipelines within the Python ecosystem, thereby enhancing both reproducibility and adaptability.

# Software Design

The MOLASS library is designed to support sustainable software development by providing an open framework that enables broad community participation and contribution. Rather than contributing to existing GUI-based tools like ATSAS or BioXTAS RAW, we chose to build a Python-first, Jupyter-centric solution designed to support AI-assisted maintenance and researcher extensibility. This design philosophy prioritizes explicit, readable code over graphical interfaces, making the analysis methodology transparent for both learning and AI-assisted maintenance. We are actively enhancing AI-readiness through systematic usability testing with AI agents and iterative improvements to API discoverability and inline documentation. The architecture emphasizes modularity and clear separation of concerns: elution curve models (EGH, SDM, EDM) are isolated as parametric functions; low-rank factorization uses standard linear algebra (Moore-Penrose pseudoinverse); and visualization is decoupled from computation. By integrating established packages (NumPy, SciPy, pybaselines, ruptures) rather than reimplementing core functionality, we reduce custom code volume and enhance long-term viability. This approach allows domain researchers to maintain and extend the code using AI-assisted development tools.

# Research Impact Statement

Molass Library has demonstrated credible research significance through its predecessor's track record [@Yonezawa:2023] and its positioning against documented limitations of alternative approaches. While CHROMIXS explicitly defers analysis of overlapping chromatographic peaks to "other methods" [@Panjkovich:2018], EFAMIX quantifies failure thresholds (signal-to-noise ratio ≥10³ required for three-component separation; peak asymmetry parameter τ≤2; baseline width separation ≥2× for reliable decomposition) [@Konarev:2021], and REGALS employs a two-stage approach combining EFA with L1 regularization [@Meisburger:mf5050], inheriting EFA's fundamental limitations in overlapping peak scenarios. Molass Library addresses these documented limitations through explicit parametric modeling of elution curves and rigorous global optimization methods that constrain solutions using SEC theory (size-dependent elution) and SAXS theory (radius of gyration consistency), widening the scope of tractable cases for overlapping peak decomposition beyond what existing methods can reliably address.

# Notable package dependencies

Molass Library is built on robust scientific Python libraries, including NumPy, SciPy, and Matplotlib. It further integrates:

* **pybaselines** [@pybaselines] for advanced baseline correction
* **ruptures** [@TRUONG2020107299] for change point detection
* **scipy.signal.find_peaks** for peak recognition

By adopting these well-maintained packages, Molass Library reduces custom code and enhances reliability. The transition from a GUI-based workflow (previously using Tkinter) to Jupyter-based scripting further streamlines reproducibility and collaboration.

# Theoretical Foundation

A central feature of Molass Library is its implementation of **low rank factorization** using elution curve models, enabling decomposition of overlapping chromatographic peaks, a common challenge in SEC-SAXS analysis. The decomposition is formulated as:

$$ M = P \cdot C \qquad (1) $$

where:

* $M$: measured data matrix
* $P$: matrix of component scattering curves
* $C$: matrix of component elution curves

The optimal solution in the least-squares sense is given by:

$$ P = M \cdot C^{+} \qquad (2) $$

where $C^{+}$ denotes the Moore-Penrose pseudoinverse [@Penrose_1955; @Penrose_1956]. This approach enables robust separation of components, even in the presence of overlapping peaks, provided suitable constraints are applied.
Moreover, interparticle interference effects can be separated by adding row vectors based on the quadratic approximation derived from SAXS theory.

![Illustration of decomposition using simulated data](docs/_static/simulated_data.png)

# Elution Curve Modeling

To address underdeterminedness and enhance interpretability, Molass Library incorporates several established elution curve models:

* **EGH**: Exponential Gaussian Hybrid [@LAN20011]
* **SDM**: Stochastic Dispersive Model [@Felinger1999]
* **EDM**: Equilibrium Dispersive Model [@Ur2021]

These models allow users to impose domain-specific constraints, thereby enhancing both the accuracy and the physical relevance of the chromatographic peak decomposition.

# Availability and Documentation

Molass Library is freely available under an open-source license at [https://github.com/biosaxs-dev/molass-library](https://github.com/biosaxs-dev/molass-library). Comprehensive documentation, including tutorials and theoretical background, is provided at [Molass Essence](https://biosaxs-dev.github.io/molass-essence/chapters/intro.html).

# AI usage disclosure

Generative AI tools (GitHub Copilot, Claude 3.5 Sonnet, ChatGPT-4) were used for the following aspects of this submission:

* **Paper text**: AI assistance was limited to improving English grammar, sentence structure, and clarity. All technical content, design decisions, and scientific claims were authored by the human authors.
* **Code generation**: Small, common code portions (e.g., standard NumPy array operations, Matplotlib plotting boilerplate) were AI-generated. All core algorithms, elution curve models, and scientific logic were designed and implemented by the human authors.
* **Documentation**: Significant portions of the tutorial notebooks and API documentation were initially drafted with AI assistance, then extensively reviewed, corrected, and refined by the human authors to ensure technical accuracy and pedagogical effectiveness.

All AI-generated content was reviewed, validated, and edited by the human authors, who made all core design decisions and remain fully responsible for the accuracy and integrity of this submission.

# Acknowledgements

This work was supported by JSPS KAKENHI Grant Number JP25K07250, and partially by Research Support Project for Life Science and Drug Discovery (Basis for Supporting Innovative Drug Discovery and Life Science Research (BINDS)) from AMED under Grant Number JP25ama121001.

# References

