# Refactor Documents Index

This folder contains all refactoring plans, design documents, and architecture analysis for molass-library and molass-legacy.

## Architecture

| Document | Topic | Status |
|---|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Repository role separation, migration levels A–C, data object consolidation | Ongoing |

## Active Plans

| Document | Topic | Status |
|---|---|---|
| [PLAN_subprocess_parity.md](PLAN_subprocess_parity.md) | GUI subprocess missing ip_*.npy; DE/NSGA2 gap; fix options | Open (#206) |

## Design Documents (completed or in-progress features)

| Document | Topic | Status |
|---|---|---|
| [DESIGN_split_optimizer_architecture.md](DESIGN_split_optimizer_architecture.md) | In-process vs subprocess split; Phase 4 implemented | ✅ Phase 4 done |
| [DESIGN_complementary_view_refactor.md](DESIGN_complementary_view_refactor.md) | Replace legacy ComplementaryView with plot_components | ✅ Implemented Jun 2026 |
| [DESIGN_inprocess_monitor.md](DESIGN_inprocess_monitor.md) | MplMonitor for in-process runs | ✅ Implemented |
| [DESIGN_terminate_inprocess.md](DESIGN_terminate_inprocess.md) | Terminate button for in-process runs | ✅ Implemented |

## How to use this folder

When starting a refactoring session, read:
1. `ARCHITECTURE.md` — for the overall migration target and current levels
2. The relevant `PLAN_*.md` — for the specific fix being worked on
3. Any `DESIGN_*.md` relevant to the component being changed

New design documents should be created here with the prefix `DESIGN_` or `PLAN_`.
