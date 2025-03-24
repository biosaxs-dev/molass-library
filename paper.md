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
    affiliation: 1
  - name: Nobutaka Shimizu
    orcid: 0000-0002-3636-1663
    corresponding: true
    affiliation: "2,1"
affiliations:
 - name: Institute of Materials Structure Science
   index: 1
   ror: 0327y7e25
 - name: Institute of Physical and Chemical Research
   index: 2
   ror: 01sjwvz98
date: 24 March 2025
bibliography: paper.bib

---

# Summary

`Molass Library` is a rewrite of MOLASS [@Yonezawa:2023] which is an analytical tool for SEC-SAXS experiment data currently hosted at [Photon Factory](https://pfwww.kek.jp/saxs/MOLASS.html). It is designed for scripting in Jupyter notebooks [@Kluyver:2016aa], thereby attaining greater flexibility compared to the predecessor thanks to the Python ecosystem diversity.

As the name suggests, SEC-SAXS experiment consists of the two parts:

* SEC - Size Exclusion Chromatograpy
* SAXS - Small Angle X-Ray Scattering

each of which has its own theoretical characteristics. Therefore, the analysis requires a balanced combination of those, which is the target of `Molass Library`.

# Statement of need

Analysis of SEC-SAXS experiment data involves several steps such as:

1. Circular Average
2. Background Subtraction
3. Trimming
4. Baseline Correcction
5. Low Rank Factorization
6. Rg Estimation (Guinier Plot)
8. ... (Kratky Plot)
9. Original Structure (Electron Density) Estimation

among which `Molass Library` currently supports only steps 3-8. For the first two steps, `SAngler` [@Shimizu:2016] can be used, while `DENSS` [@Grant:2018] is available for the last step. For all those steps, there already exist alternative software tools with various coverage. The most comprehensive and popular tool is `ATSAS` [@Manalastas-Cantos:ge5081], which is proprietary and consists of a couple of dozens of command interface programs for each responsible step. Other tools include `BioXTAS RAW` [@Hopkins:jl5075], which is an open-source GUI application for such executable programs, some of which are open and others of which include closed ATSAS. In such state of software availability for SEC-SAXS experiments, `Molass Library` can make larger part of tools more open and flexible powered by the Python ecosystem.

![Logo of Molass Library created by K. Yatabe](docs/_static/molass_256.png)

# Notable package dependence

NumPy [@Harris2020], SciPy [@Virtanen2020] and Matplotlib [@Hunter:2007] are necessity. Moreover, it is notable that `Molass Library` reduced significant volume of codes by the use of following packages.

* `pybaselines` [@pybaselines] for Baseline Correcction
* `ruptures` [@TRUONG2020107299] for Change Point Dedection

Likewise, basic part of peak recognition was replaced by `scipy.signal.find_peaks` although elaborate cutomization is still required for practical recognition.

# Theoretical focus

"Low Rank Factorization", the most important feature of `Molass Library`, is related to the decomposition of species contained in the sample, which is first attained physically by the Size Exclusion Chromatograpy. When the chromatographic peaks are sufficiently separated, the decomposition is easy. Otherwise it is challenging so that ... 

$$ M = P \cdot C  $$

$$ P = M \cdot C^{+}  $$


# Acknowledgements

This research was partially supported by the Platform Project for Supporting Drug Discovery and Life Science Research [Basis for Supporting Innovative Drug Discovery and Life Science Research (BINDS)] from AMED under grant numbers ...

# References

