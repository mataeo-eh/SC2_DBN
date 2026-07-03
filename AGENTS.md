# DOX + Munch Contract

## Purpose

- This file is the root work contract for `local-play-bootstrap-main`.
- DOX keeps durable project contracts current. jdocmunch and jcodemunch provide semantic retrieval so agents can understand the codebase before changing it.
- Use both systems together: retrieve context intelligently, make architecture-aware edits, then update durable docs so future retrieval and human review stay coherent.

## Core Contract

- `AGENTS.md` files are binding contracts for their subtrees.
- Work products, source materials, instructions, records, assets, and durable docs must remain understandable from the nearest applicable `AGENTS.md` plus every parent `AGENTS.md` above it.
- Do not rely on memory for local rules. Re-read the applicable DOX chain in the current session before editing.
- Before running any Python command, check for a project virtual environment at the relevant repo boundary. Run Python through that venv's Python shim, such as `.venv\Scripts\python.exe`, `SC2-gamestate-extractor\.venv\Scripts\python.exe`, or `Thesis_ML\.venv\Scripts\python.exe`.

## Retrieval Contract

- Prefer semantic retrieval before broad manual file reading when the task involves unfamiliar code, architecture, symbols, or documentation.
- Use `jcodemunch` for source-code navigation, symbol discovery, caller/callee context, and AST-aware retrieval.
- Use `jdocmunch` for Markdown, text, reStructuredText, specs, plans, READMEs, and other durable documentation.
- If an index already exists for the relevant repo or submodule, update it incrementally before relying on it for non-trivial edits.
- If no index exists, do not silently start a full monorepo index during unrelated work. The first `jcodemunch` index of this repository and its submodules can be slow; ask the user before starting a full first-time index.
- When indexing is appropriate, scope it to the smallest useful boundary first: root workspace, `SC2-gamestate-extractor`, `Thesis_ML`, or a specific bot submodule.
- After meaningful code or documentation changes, refresh the relevant jcodemunch and/or jdocmunch index when practical. If an index refresh is skipped, report why.
- Treat Munch results as navigation and context, not authority. Verify important behavior against source files, tests, and the applicable DOX chain before editing.

## Architecture Contract

- Every code change must improve or preserve the architecture of the whole project, not only satisfy the nearest feature request.
- Before editing, identify the subsystem boundary, existing ownership, data flow, public API, and downstream consumers that could be affected.
- Reuse existing helpers, schemas, adapters, fixtures, and workflows. Do not create a new shared helper when an adequate one already exists.
- If two features need the same internal logic, prefer extracting a cohesive shared helper at the right ownership boundary over duplicating logic.
- Keep changes integrated across extraction, replay data, ML training inputs, docs, tests, and bot workflows where those concerns touch.
- Avoid narrow fixes that create hidden coupling, inconsistent schemas, incompatible data shapes, or parallel conventions.
- Preserve semantic distinctions in domain behavior. Do not flatten lifecycle, replay, ML, or strategy concepts merely to make a local implementation simpler.
- Keep generated data, heavy artifacts, logs, caches, and local environment state out of durable contracts unless the workflow explicitly owns them.

## Read Before Editing

1. Read this root `AGENTS.md`.
2. Identify every file or folder you expect to touch.
3. Walk from the repository root to each target path.
4. Read every `AGENTS.md` found along each route.
5. If a parent `AGENTS.md` lists a child `AGENTS.md` whose scope contains the path, read that child and continue from there.
6. Use the nearest `AGENTS.md` as the local contract and parent docs for repo-wide rules.
7. If docs conflict, the closer doc controls local details, but no child doc may weaken DOX, the retrieval contract, the Python environment rule, or the architecture contract.

## Update After Editing

- Every meaningful change requires a DOX pass before the task is done.
- Update the closest owning `AGENTS.md` when a change affects purpose, scope, ownership, responsibilities, durable structure, contracts, workflows, operating rules, required inputs, outputs, permissions, constraints, side effects, artifacts, or stable user preferences.
- Update parent docs when parent-level structure, ownership, workflow, or child indexes change.
- Update child docs when parent changes alter local rules.
- Remove stale or contradictory text immediately.
- Small edits that do not change behavior or contracts may leave docs unchanged, but the DOX pass still must happen.
- When code architecture changes, update both the relevant DOX contract and the relevant Munch index when practical, so semantic retrieval and durable documentation converge.

## Hierarchy

- The root `AGENTS.md` is the DOX rail for project-wide instructions, global preferences, architecture rules, retrieval rules, and the top-level Child DOX Index.
- Child `AGENTS.md` files own domain-specific instructions and their own Child DOX Index.
- Each parent explains what its direct children cover and what stays owned by the parent.
- The closer a doc is to the work, the more specific and practical it must be.
- Create a child `AGENTS.md` when a folder becomes a durable boundary with its own purpose, rules, responsibilities, workflow, materials, or quality standards.

## Child Doc Shape

Default section order:

- Purpose
- Ownership
- Local Contracts
- Work Guidance
- Verification
- Child DOX Index

Work Guidance must reflect current standards. Verification must reflect existing checks. Leave those sections empty when no specific standards or checks exist yet.

## Style

- Keep docs concise, current, and operational.
- Document stable contracts, not diary entries.
- Put broad rules in parent docs and concrete details in child docs.
- Prefer direct bullets with explicit names.
- Do not duplicate rules across many files unless each scope needs a local version.
- Delete stale notes instead of explaining history.
- Trim obvious statements, repeated rules, misplaced detail, and warnings for risks that no longer exist.

## Verification

- Use existing verification closest to the changed scope.
- Root Python commands must use the root venv shim after confirming `.venv` exists.
- `SC2-gamestate-extractor` Python commands must use that submodule's venv shim after confirming it exists.
- `Thesis_ML` Python commands must use that submodule's venv shim after confirming it exists.
- Do not run expensive replay processing, model training, large indexing, or broad integration jobs unless the task requires them or the user approves.

## Closeout

1. Re-check changed paths against the DOX chain.
2. Update nearest owning docs and any affected parents or children.
3. Refresh every affected Child DOX Index.
4. Remove stale or contradictory text.
5. Refresh relevant jcodemunch or jdocmunch indexes when practical; report skipped refreshes.
6. Run existing verification when relevant.
7. Report docs intentionally left unchanged and why.

## User Preferences

- When the user requests a durable behavior change, record it here or in the relevant child `AGENTS.md`.
- Agents must integrate jdocmunch and jcodemunch with DOX: use semantic retrieval to understand the codebase, then update DOX when changes alter durable architecture or workflows.
- Code changes must be made with whole-project architecture in mind. Avoid shortest-path feature patches that ignore neighboring systems, shared helpers, schemas, or downstream consumers.
- `Thesis_ML` models must never receive absolute game time, frame numbers, `game_loop`, or timestamp-derived values. Keep time only as non-model metadata for ordering or post-sampling evaluation; sequence position is Llama 3.1-style frequency-scaled RoPE configured in YAML.

## Child DOX Index

- `Thesis_ML/AGENTS.md`: Local contract for thesis ML preprocessing, budget-driven replay windows, dynamic collation, model training, and verification.
- `SC2-gamestate-extractor/`: Git submodule for replay parsing, game-state extraction, lifecycle tracking, parquet output, feature engineering, extractor tests, and its own uv-managed Python project.
- `Thesis_ML/`: Git submodule for thesis ML research, schemas, specs, configs, experiments, notebooks, model code, and its own uv-managed Python project.
- `Thesis_ML/scripts/`: Thesis dataset analysis utilities. `estimate_context_window.py` derives the root quickstart parquet location from the repository layout and writes token-length reports under `Thesis_ML/scripts/output/` without persisting machine-specific paths.
- `bots/`: Bot workspace containing local bot folders plus `reallySC2Bot`, `whatSC2Bot`, and `whySC2Bot` submodules. Treat each bot submodule as an independent code boundary.
- `tests/`: Root test suite for replay extraction behavior using mocks and focused regression coverage.
- `docs/`: Root architecture, usage, API, planning, research, troubleshooting, and data dictionary documentation.
- `research/` and `Reference_Files/`: Investigation notes, historical extraction references, API findings, and prototype material. Preserve provenance and avoid treating old references as current behavior without source verification.
- `ML_PoC/`: Root ML proof-of-concept notebooks, tokenization experiments, and prototype assets. Keep data schemas and tokenization assumptions aligned with extractor outputs and `Thesis_ML/`.
- `scripts/` and `diagnostics/`: One-off and reusable operational checks for replay data, raw API behavior, migration, and debugging.
- `examples/`, `README_LOCAL_PLAY.md`, `README_SC2_PIPELINE.md`, `IMPLEMENTATION_SUMMARY.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, and `TODO.md`: Root usage, onboarding, history, and project-management documentation.
- `config/`, `config_new/`, `schemas/`, `game_info/`, `maps/`, `prompts/`, and `runners/`: Runtime configuration, schema material, SC2 metadata, map assets, prompt material, and execution helpers.
- `python-sc2.wiki/`, `plan/`, and `img/`: Reference docs, planning material, and image assets.
- `data/`, `replays/`, `logs/`, `.pytest_cache/`, `__pycache__/`, and venv folders: local/generated state. Do not make durable architecture claims from their contents without checking whether they are intended source materials.
