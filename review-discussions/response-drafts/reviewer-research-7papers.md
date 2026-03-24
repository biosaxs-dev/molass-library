# Reviewer Research: 7-Paper Survey Results

**Date**: 2026-03-25  
**Method**: Extracted actual reviewers from 7 JOSS papers spanning SEC-SAXS domain and clean Python API design  
**Status**: Complete — resulted in supplementary draft `reviewer-suggestions-supplementary.md`

---

## Source Papers and Reviewers

| Paper | Issue | Track | Published | Reviewers |
|---|---|---|---|---|
| PeakPerformance (BCM, LC-MS/MS peak fitting) | #7313 | BCM | Dec 2024 | **Adafede**, **lazear** |
| hplc-py (HPLC chromatogram quantification) | #6270 | BCM | Feb 2024 | **florian-huber**, **Kastakin** |
| DebyeCalculator (GPU small-angle scattering) | #6024 | Physics/Eng | Feb 2024 | **marcocamma**, **elena-pascal**, **KedoKudo** |
| CADET-Core (chromatography simulation, C++) | #7881 | BCM | Jul 2025 | **bdice**, **goxberry** |
| idpflex (SAXS + intrinsically disordered proteins) | #1007 | — | Dec 2018 | **gjeuken** |
| alchemlyb (alchemistry Python library) | #6934 | BCM | Sep 2024 | **glycodynamics**, **ryankzhu** |
| anndata (annotated data matrices) | #4371 | BCM | Sep 2024 | **nlhepler**, **rcannood** |

**Note**: #7313, #6270, #6024 were already researched in the previous session (confirmed all 4 existing-draft candidates).  
This session adds: #7881, #1007, #6934, #4371.

---

## Deduplication against Existing Draft

Already suggested to zhubonan (in `reviewer-suggestions-to-zhubonan.md`):  
**KedoKudo**, **florian-huber**, **Adafede**, **lazear**

New candidates from this survey (10):  
Kastakin, marcocamma, elena-pascal, bdice, goxberry, gjeuken, glycodynamics, ryankzhu, nlhepler, rcannood

---

## Activity & Relevance Assessment (New Candidates)

| Handle | Real identity/affil | Contrib/year | Domain fit | Notes |
|---|---|---|---|---|
| **elena-pascal** | Physics/diffraction, UK (@illumion-ltd) | **450** | ⭐⭐⭐ | Reviewed DebyeCalculator (SAS) directly; contributes to scikit-image; active |
| **bdice** | Bradley Dice, NVIDIA RAPIDS; PhD Physics & Scientific Computing | **5,202** | ⭐⭐ | Reviewed CADET-Core (BCM); scientific Python expert; extremely active |
| **goxberry** | Geoffrey Oxberry, ex-LLNL, now DataDog | 574 | ⭐ | Reviewed CADET-Core; now in industry (DataDog), less domain-focused |
| **marcocamma** | Marco Cammarata, ESRF Grenoble physicist | **3** | ⭐⭐⭐ | Direct SAS/X-ray domain; nearly inactive on GitHub — may still respond |
| **gjeuken** | Gustavo Jeuken, Vrije Universiteit Amsterdam | 33 | ⭐⭐ | Reviewed idpflex (SAXS + IDP); low-moderate activity |
| **Kastakin** | Lorenzo Castellino, PhD student, Univ. Turin | 6 | ⭐⭐ | Reviewed hplc-py (BCM); analytical chemistry; very low activity |
| **glycodynamics** | (alchemlyb reviewer, free energy/chem) | ? | ⭐ | BCM chemistry; not SAXS-specific |
| **ryankzhu** | (alchemlyb reviewer) | ? | ⭐ | BCM chemistry; not SAXS-specific |
| **nlhepler** | (anndata reviewer) | ? | ⭐ | General Python scientific library; not domain-specific |
| **rcannood** | Robin Cannoodt, bioinformatics/R | ? | ⭐ | Broad Python/R scientific computing; not domain-specific |

---

## Recommendation

### Top 2 new candidates to add to reviewer suggestions:

1. **elena-pascal** — Strongest new find. 450 contributions/year (active), directly reviewed DebyeCalculator (GPU small-angle scattering, #6024), contributes to scikit-image, works in scientific Python computing (illumion-ltd, UK). Domain + Python API quality — perfect two-angle fit.

2. **bdice** (Bradley Dice) — 5,202 contributions/year (extremely active), PhD Physics & Scientific Computing from Glotzerlab (particle trajectory analysis), now NVIDIA RAPIDS developer (strong Pythonic scientific computing). Reviewed CADET-Core (BCM chromatography simulation, #7881). Strong reviewer with rigorous scientific software standards.

### Honorable mentions (consider if primary candidates decline):

- **marcocamma** — ESRF physicist with direct X-ray expertise; nearly inactive GitHub (3 contrib/year) but may respond via JOSS invitation; high domain credibility.
- **gjeuken** — VU Amsterdam, reviewed idpflex (SAXS + IDP proteins, #1007); 33 contrib/year; good domain fit.

### Not recommended:
- **goxberry** — now at DataDog; less domain-focused
- **Kastakin** — 6 contrib/year; too low activity for reliable review
- **glycodynamics**, **ryankzhu**, **nlhepler**, **rcannood** — too distant from SEC-SAXS/spectroscopy domain

---

## Key Observation

All 4 candidates from the existing draft (KedoKudo, florian-huber, Adafede, lazear) were found in these 7 papers — confirming the earlier research was sound. The 7-paper expanded search adds **elena-pascal** as the most significant new find: direct SAS reviewer + active Python scientific computing contributor.
