<!-- ============================================================
  SUPPLEMENTARY REVIEWER SUGGESTIONS — POST #2
  Copy the text between the dashed lines into the GitHub comment box
  ============================================================ -->

---

Following further research into JOSS review history, I would like to consolidate my reviewer suggestions into a single list for convenience. The candidates below were selected primarily for their expertise in chromatographic separation and scattering data analysis, but a few were also included with software API design quality in mind, as molass places particular emphasis on a clean, accessible Python interface for scientific users. These are the candidates I consider most suitable, including those I mentioned previously:

- **[KedoKudo](https://github.com/KedoKudo)** (Chen Zhang) — Computational Scientist at Oak Ridge National Laboratory; focuses on scientific software for neutron/X-ray scattering data reduction and analysis, and AI-assisted scientific workflows. Reviewed a GPU-accelerated small-angle scattering Python package for JOSS ([review #6024](https://github.com/openjournals/joss-reviews/issues/6024)).

- **[florian-huber](https://github.com/florian-huber)** (Florian Huber) — Professor at HSD Düsseldorf; develops Python tools for mass spectrometry data processing and similarity scoring (matchms, spec2vec), with expertise in scientific software and machine learning applied to analytical chemistry. Reviewed an HPLC chromatography analysis package for JOSS ([review #6270](https://github.com/openjournals/joss-reviews/issues/6270)).

- **[Adafede](https://github.com/Adafede)** (Adriano Rutz) — Pharmaceutical Scientist at ETH Zürich; specializes in computational metabolomics and LC-MS/MS-based characterization of complex biological matrices. Reviewed a chromatographic peak detection and quantification package for JOSS ([review #7313](https://github.com/openjournals/joss-reviews/issues/7313)).

- **[lazear](https://github.com/lazear)** (Michael Lazear) — Developer of Sage, a high-performance proteomics search and quantification tool; strong expertise in chromatographic data processing and scientific software engineering. Reviewed the same chromatographic peak analysis package for JOSS ([review #7313](https://github.com/openjournals/joss-reviews/issues/7313)).

- **[elena-pascal](https://github.com/elena-pascal)** — Physicist working in scientific Python computing (UK); has hands-on experience with small-angle scattering data and diffraction analysis, including having reviewed a GPU-accelerated small-angle scattering package for JOSS ([review #6024](https://github.com/openjournals/joss-reviews/issues/6024)). Active contributor to scikit-image. Combines domain knowledge in X-ray scattering with practical Python library development experience.

- **[bdice](https://github.com/bdice)** (Bradley Dice) — Scientific software developer at NVIDIA RAPIDS; PhD in Physics and Scientific Computing (Glotzerlab, University of Michigan). Reviewed a high-performance chromatography simulation package for JOSS ([review #7881](https://github.com/openjournals/joss-reviews/issues/7881), BCM track). Strong expertise in scientific Python API design and reproducible software practices.

---

<!-- ============================================================
  END OF COPY REGION
  ============================================================ -->

---

## File Metadata

**Posted by**: nshimizu0721 (Shimizu)  
**Target**: JOSS pre-review issue #9424 — reply to existing thread  
**Date drafted**: 2026-03-24  
**Status**: DRAFT — ready to post

---

## Background (not for posting)

Candidates #1–4 were in the March 23 post. Candidates #5–6 are newly found via systematic extraction of reviewers from 7 relevant JOSS papers.  
Full research notes: `reviewer-research-7papers.md`

| Handle | Why recommended | Activity | Source paper |
|---|---|---|---|
| KedoKudo | X-ray/neutron scattering, AI workflows | — | #6024 (DebyeCalculator) |
| florian-huber | Analytical chemistry Python tools | — | #6270 (hplc-py) |
| Adafede | LC-MS/MS, metabolomics | — | #7313 (PeakPerformance) |
| lazear | Proteomics, chromatographic processing | — | #7313 (PeakPerformance) |
| elena-pascal | Direct SAS reviewer; scikit-image contributor; active | 450 contrib/year | #6024 (DebyeCalculator) |
| bdice | PhD Physics & Sci. Computing; BCM track reviewer; extremely active | 5,202 contrib/year | #7881 (CADET-Core) |

Honorable mentions if primary candidates are unavailable:
- **marcocamma** — ESRF physicist (direct X-ray domain), low GitHub activity (3/year)
- **gjeuken** — VU Amsterdam, reviewed idpflex (#1007, SAXS + IDP proteins), 33 contrib/year
