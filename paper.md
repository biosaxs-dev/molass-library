---
title: 'Molass Library: A Python package for SEC-SAXS data analysis'
tags:
  - Python
  - SEC-SAXS
  - Bio-SAXS
authors:
  - name: Masatsuyo Takahashi
    orcid: 0009-0007-1466-5563
    corresponding: false    
    affiliation: "1,2"
  - name: Nobutaka Shimizu
    orcid: 0000-0002-3636-1663
    corresponding: true
    affiliation: "3,1,2"
affiliations:
  - name: Structural Biology Research Center, Institute of Materials Structure Science
    index: 1
  - name: Institute of Materials Structure Science
    index: 2
    ror: 0327y7e25
  - name: Institute of Physical and Chemical Research
    index: 3
    ror: 01sjwvz98
date: 24 March 2025
bibliography: paper.bib

---

# Summary

Molass Library is a rewrite of MOLASS [@Yonezawa:2023], an analytical tool for SEC-SAXS experiment data currently hosted at [Photon Factory](https://pfwww.kek.jp/saxs/MOLASS.html), Japan. It is designed for scripting in Jupyter notebooks [@Kluyver:2016aa], thereby achieving greater flexibility than its predecessor, thanks to the diversity of the Python ecosystem.

An SEC-SAXS experiment consists of two independent parts:

* SEC - Size Exclusion Chromatography
* SAXS - Small Angle X-Ray Scattering

Each is based on its own theoretical discipline, and analysis requires a balanced combination of both, which is the aim of the Molass Library.

![Logo of Molass Library designed by K. Yatabe](docs/_static/molass_256.png)

# Statement of need

Analysis of SEC-SAXS experiment data involves several steps. For clarity, a typical workflow includes:

1. Circular Averaging
2. Background Subtraction
3. Trimming
4. Baseline Correction
5. Low Rank Factorization
6. Rg Estimation – Guinier Plot [@Guinier_1939]
7. Shape Inspection – Kratky Plot [@Kratky_1963]
8. Electron Density Estimation

Among these, the Molass Library currently supports steps 3–7. For the first two steps, SAngler [@Shimizu:2016] can be used, while DENSS [@Grant:2018] is available for the last. Alternative software tools already exist with varying coverage of these steps. The most comprehensive and popular tool is ATSAS [@Manalastas-Cantos:ge5081], which is proprietary (closed-source) and consists of a standard SAXS suite of command-line interface programs for each step, coupled with GUI programs. Other tools include BioXTAS RAW [@Hopkins:jl5075], an open-source GUI application for running such modular programs, some of which are open-source and others of which include the ATSAS suite. In this semi-closed ecosystem of SEC-SAXS tools, the Molass Library is expected to help researchers better understand, improve, and utilize their tools by making a larger part of the workflow more open and flexible, in conjunction with the Python ecosystem.

# Notable package dependencies

In addition to the fundamental dependencies on NumPy [@Harris2020], SciPy [@Virtanen2020], and Matplotlib [@Hunter:2007], the Molass Library has replaced a significant volume of custom code with the following packages:

* pybaselines [@pybaselines] for baseline correction
* ruptures [@TRUONG2020107299] for change point detection

Similarly, the core functionality for peak recognition has been replaced by `scipy.signal.find_peaks`, although further adjustments are still required for practical application.

To reduce dependencies, much of the GUI implementation previously done using Tkinter [@lundh1999introduction] is no longer needed, as it has been replaced by scripting in Jupyter notebooks.

# Theoretical focus

Among the steps listed above, low rank factorization[^1] using elution curve models is the most distinctive feature of the Molass Library. This process is directly related to the decomposition of species in the sample, which is first achieved physically by size exclusion chromatography and then refined through logical estimation and optimization in the software. When the chromatographic peaks are well separated, decomposition is relatively straightforward. However, significant peak overlap makes decomposition challenging due to underdeterminedness[^2] and noise. Addressing these challenges is beyond the scope of this paper and may be explored in future versions of the library.

Here, we describe the essence of the simpler case to illustrate the basic approach. For clarity, we use matrix notation in the following discussion. Ideally, the decomposition can be expressed as follows:

$$ M = P \cdot C \qquad \qquad (1) $$

where:

* $M$: matrix of measured data,
* $P$: matrix whose columns are component scattering curves,
* $C$: matrix whose rows are component elution curves.

[^1]: While this is often called Low Rank Approximation, we prefer the term "Factorization" because, in this context, it better matches the psychological orientation toward decomposition.

[^2]: By "underdeterminedness," we mean the situation where many decomposition candidates are found and we have no definite information to reduce them to a smaller number that can be studied effectively.

See the following figure for intuition about this decomposition.

![Illustration of Decomposition using Simulated Data](docs/_static/simulated_data.png)

Using the above relation, the solution can be calculated, in the sense of footnote[^3], as follows:

[^3]: $P$ is determined as the best possible solution which minimizes $\| M - P \cdot C \|$.

$$ P = M \cdot C^{+} \qquad \qquad (2) $$

where

* $C^{+}$: Moore-Penrose inverse [@Penrose_1955; @Penrose_1956]

Note that in equations (1) and (2), $P$ and $C$ are mathematically equivalent, but not physically identical. In practice, we obtain $P$ from $M$ and $C$, since $M$ is given and it is easier to estimate $C$ than $P$.[^4]

[^4]: For more details, see the corresponding chapter of the online document [Molass Essence](https://freesemt.github.io/molass-essence/chapters/04/lowrank.html).

# Elution curve models – modeling approach

In contrast to our approach, some model-free methods such as REGALS [@Meisburger:mf5050] have been reported. However, to address underdeterminedness, we believe it is essential to reduce the degrees of freedom by applying constraints[^5] from appropriate models, as included in the Molass Library, namely:

* EGH: Exponential Gaussian Hybrid [@LAN20011]
* SDM: Stochastic Dispersive Model [@Felinger1999]
* EDM: Equilibrium Dispersive Model [@Ur2021]

depending on the characteristics of the data. The strengths and weaknesses of these models are described in detail in the Molass Library's online documentation.

[^5]: The meaning of "constraints" is left abstract here for brevity. It should be made precise in the context of model application, not only from the models themselves but also by additional customization adjusted to reality, which will be discussed elsewhere.

# Acknowledgements

This research was partially supported by the Platform Project for Supporting Drug Discovery and Life Science Research [Basis for Supporting Innovative Drug Discovery and Life Science Research (BINDS)] from AMED under grant numbers ...

# References

