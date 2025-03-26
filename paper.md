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

Literally, SEC-SAXS experiment consists of the two independent parts:

* SEC - Size Exclusion Chromatograpy
* SAXS - Small Angle X-Ray Scattering

each of which is based on its own theoretical discipline, indicating the fact that the analysis requires a balanced combination of those, which is the target of `Molass Library`.

![Logo of Molass Library designed by K. Yatabe](docs/_static/molass_256.png)

# Statement of need

Analysis of SEC-SAXS experiment data involves several steps. To list a simplest course for discussion:

1. Circular Average
2. Background Subtraction
3. Trimming
4. Baseline Correcction
5. Low Rank Factorization
6. Rg Estimation - Guinier Plot [@Guinier_1939]
7. Shape Inspection - Kratky Plot [@Kratky_1963]
8. Original Structure (Electron Density) Estimation

among which `Molass Library` currently supports only steps 3-7. For the first two steps, `SAngler` [@Shimizu:2016] can be used, while `DENSS` [@Grant:2018] is available for the last. For all those steps, there already exist alternative software tools with various coverage. The most comprehensive and popular tool is `ATSAS` [@Manalastas-Cantos:ge5081], which is proprietary (closed-source) and consists of a SAXS-oriented suite of command line interface programs for each responsible step, coupled with GUI programs for them. Other tools include `BioXTAS RAW` [@Hopkins:jl5075], which is an open-source GUI application for running such executable modular programs, some of which are open-source and others of which include the ATSAS suite. In such a semi-closed state of tools for SEC-SAXS experiments, `Molass Library` is expected to help researchers better understand, improve, and utilize their tools by making larger part of the tools more open and flexible together with the Python ecosystem.

# Notable package dependence

Setting aside the fundamental necessity of NumPy [@Harris2020], SciPy [@Virtanen2020] and Matplotlib [@Hunter:2007], `Molass Library` replaced significant volume of custom codes by using the following packages.

* `pybaselines` [@pybaselines] for Baseline Correcction
* `ruptures` [@TRUONG2020107299] for Change Point Dedection

Likewise, the basic part of peak recognition was replaced by `scipy.signal.find_peaks` although elaborate cutomization is still required for practical recognition.

For less dependence, large part of GUI implementation, which was previouly done using Tkinter [@lundh1999introduction], is no longer needed because it has been replaced by the scripting in Jupyter notebooks.

# Theoretical focus

Among the above mentioned steps, Low Rank Factorization[^1] using elution curve models is the most distinctive feature of `Molass Library`. It is directly related to the decomposition of species contained in the sample, which is first attained physically by the Size Exclusion Chromatograpy, followed by logical estimation and optimization of the software. When the chromatographic peaks are sufficiently separated, the decomposition is relatively simple. Otherwise, i.e., when the peaks overlap widely, it becomes challenging due to underdeterminedness[^2] from noise, the handling of which is beyond the scope of this paper and possibly might be studied using the future versions of this library.

Here, we decribe the essense of easier part to give a basic idea of what it is all about. For discussion, it is convinient to use matrices. Ideally, then, the decomposition should be expressed as follows:

$$ M = P \cdot C \qquad (1) $$

where the symbols are

* $M$ : matrix of measured data,
* $P$ : matrix made of columns of component scattering curves,
* $C$ : matrix made of rows of component elution curves.

[^1]: Where it is often also called Low Rank Approximation, we prefer the word "Factorization" because, in this context, the latter word in mathematics matches better to the decomposition in experiments.

[^2]: By "underdeterminedness", we mean here the situation where many decomposition candidates are found and we have no definite information to reduce them to a fewer number which can be studied effectively.

See the following figure to get intuition of this decomposition.

![Illustratin of Decomposition using Simulated Data](docs/_static/simulated_data.png)

Using the above relation, the solution can be calculated, in the sense of footnote[^3], as follows:

[^3]: $P$ is determined as the best possible solution which minimizes $\| M - P \cdot C \|$.

$$ P = M \cdot C^{+} \qquad (2) $$

where

* $C^{+}$ : Moore-Penrose inverse. [@Penrose_1955; @Penrose_1956]

Note that in formula $(1)$, $P$ and $C$ are equally eligible mathematically, but physically not. In fact, we get $P$ from $M$ and $C$, because $M$ is given and it is easier to estimate $C$ rather than $P$. The reason for this comes from the SEC principle [@Striegel_2009] where the component particles elute in the decsending order of particle size, namely the larger comes earlier, resulting in curves with distant peaks, each of which is relatively easy to model as mentioned later.

For scattering curves on the other hand, to the best of our knowledge, we have classical models only for extreme regions, namely, Guinier Approximation [@Guinier_1939] for small angle regions and Porod's law [@Porod_1951] for larger angle regions, and none for intermediate regions. From our experience, models just smoothly linking those extreme regions, as the one [@Hammouda:ce5078] used in the above figure, do not seem applicable at least to protein samples.

# Denoising $M$

For noisy data from real experiments, the equation $(1)$ should be interpreted as:

$$ \min_{P,C} \| M - P \cdot C \| \qquad (3) $$

As commonly known, we can denoise $M$ by ignoring the insignificant tail[^4] of the following expansion made from SVD - Singular Value Decomposition - based on the linear structure expected in the data.

$$ M = \sum_{i=1}^{n} \sigma_i u_i v_i^* $$

where

* $n \leq \min(rows, columns)$ : the rank of $M$,
* $\sigma_i$ : ith singular value,
* $u_i$ : ith row vector of the unitary matrix usually denoted by $U$,
* $v_i^*$ : traspose of ith row vector of the unitary matrix usually denoted by $V$.

Reducing $\| M - P \cdot C \|$ by using the denoised $M$ in place of the original, we can expect a better estimation as performed in the library. 

[^4]: terms where $n \geq i \geq r$ assuming the target rank is r, which is supposed to be the number of components in cases of simple assumption. Otherwize, e.g, if any significant interparticle effects are suspected, this number should be duly incremented. `Molass Library` can deal with this issue by adding extra quadratic rows to $C$ when the concentration dependence can be assumed linear.

# Elution curve models - modeling approach

While some model-free approaches like `REGALS` [@Meisburger:mf5050] have been reported, to cope with the underdeterminedness, we believe it is essential to reduce the degree of freedom by the contraints[^5] from appropriate models as included in `Molass Library`, namely:

* `EGH` : Exponential Gaussian Hybrid [@LAN20011],
* `SDM` : Stochastic Dispersive Model [@Felinger1999],
* `EDM` : Equilibrium Dispersive Model [@Ur2021],

depending on the state of data. Strength and weakness of these models are well distinguished in `Molass Library` online documentation.

[^5]: The meaning of "contraints" is abstract here. It should be made precise in the context of model application not only from the models themselves but also by additional cutomization adjusted to reality, which will be disscussed elsewhere.

# Acknowledgements

This research was partially supported by the Platform Project for Supporting Drug Discovery and Life Science Research [Basis for Supporting Innovative Drug Discovery and Life Science Research (BINDS)] from AMED under grant numbers ...

# References

