# Test: REMAP-CAP Q7 (which child statements are affected when a parent document changes) as rules

Rebuilds early-clinical-design-research `remapcap-design-modules` step 5 part 1 (read at 8c374cc):
script `07_inheritance_readings.py` (what each DSA statement on the Core, PANDA or SAA points at and which
section it resolves to) and script `08_version_readings.py` (R6s / R7: statements on Core sections changed
in 4.1, and the Core versions they resolve to). Competency question Q7, case questions R6s and R7.

What is new compared with the Python build: no rule computes "changed in 4.1". The same rules run twice,
once with Core 4.0 as the only Core and once with Core 4.1 added. A statement is affected when the section
texts it derives from (provenance graph) differ between the two runs. Version binding here means: re-run
on the new parent version and compare.

## Inputs (`inputs/`, sha256 in `inputs/MANIFEST.sha256`)
- `ecdr-8c374cc/remapcap-design-modules/` (early-clinical-design-research at 8c374cc). Public.
  - `output/step1/cross_references.csv`: the DSA → Core / PANDA / SAA statements, with step 1's relation
    labels.
  - `output/documents.csv`: version and date from each document's header, plus the PDF url and sha256.
  - `sources/topic_rules.csv`: the 18 topic rules (mapping data).
  - `output/step5/inheritance_readings.csv`, `output/step5/statement_versions.csv`: used only by the
    comparison.
- `not-redistributed/sections.csv`: whole-section text of the 12 documents, step 1 text layer. **Not
  redistributed**, the same as in early-clinical-design-research (`.gitignore` there). Rebuilt 2026-11-14:
  - downloaded the 12 PDFs from the `documents.csv` urls; every sha256 matched;
  - ran `scripts/01_extract_structure.py` with gate 1 skipped (it reads Plan 1's step 2 `sections.csv`,
    which is also git-ignored). Gate 2 passed.
  - The regenerated `cross_references.csv` and `headings.csv` are byte-identical to the committed ones.
  - Scripts 07 and 08 then reproduce the committed `inheritance_readings.csv` and `statement_versions.csv`
    byte for byte.
  - `facts.trig` and `facts_core41.trig` carry the same section text, so they are not redistributed
    either. `out/` holds no section text.

## Files
- `build_facts.py`: transcription only. It writes three files:
  - `facts.trig`: 139 statements; 11 documents; PANDA and Core 4.0 sections.
  - `facts_core41.trig`: the Core 4.1 document and its sections, i.e. the new parent version.
  - `mapping.trig`: `topic_rules.csv` as the graph `urn:jt:g:topic-rules`.
- `transition.trig`: the V-transition reading as mapping data. It holds the Core 7.6.2 sentence, the
  endpoint sections it protects, and how "this amendment", "dated" and "previous versions" are read
  (accepted 2026-10-25).
- `rules_q7.trig`: 15 rules.
  - **I1**: a section in any version is an expression of the version-independent section with the same
    layer and number. This is the node-identity decision.
  - **D0, D1**: supersession by header date, and the version in force (V-current).
  - **TT1-TT3**: T-target.
  - **TB1-TB2**: T-binding.
  - **TM1, TM2, TR1**: T-topic. Every match is logged. "First match wins" is a negative condition: a
    match shadowed by a lower-order match does not resolve.
  - **TU1-TU2**: not resolved, with the reason.
  - **VC1**: V-current, resolves to the expression in the version in force.
  - **VT1**: V-transition. It fires only if the Core in force contains the transition sentence.
- `check.py`: the gate on the mapping data (as in script 07), Part A, Part B.
- `out/core40/`, `out/core41/`: for each run, `q7_readings.ttl`, `prov.ttl`, `firings.ttl` and
  `compiled.rq`. Firing graphs are named per run (`urn:q7:firing:core40:…`, `urn:q7:firing:core41:…`).

## Run
From the repository root: `./run_remapcap.sh` (not part of `run_all.sh`, because `sections.csv` is not redistributed). Or, in this folder:
```
python3 build_facts.py
python3 ../../machinery/rulerun.py --rules rules_q7.trig mapping.trig transition.trig --facts facts.trig --out out/core40 --output q7_readings.ttl --firing-ns urn:q7:firing:core40:
python3 ../../machinery/rulerun.py --rules rules_q7.trig mapping.trig transition.trig --facts facts.trig facts_core41.trig --out out/core41 --output q7_readings.ttl --firing-ns urn:q7:firing:core41:
python3 check.py
```

## Result (2026-11-14)
- **Part A, inheritance readings:** 139 from the rules, 139 from script 07; all 139 identical on all 13
  columns. Resolution, target titles and target change are compared as sorted sets. 125 resolved; 6
  version-scoped; 3 unresolved (no topic rule matches); 5 SAA.
- **Part B, affected statements:** 54 statements whose section inputs differ between the runs. This is
  the same set as the readings with a target change. Against `statement_versions.csv`: 54/54 identical on
  every column except `first_change_in_4_1`, a display excerpt from another pipeline's diff.
  - R7: 4.1 only 32; 4.1 + 4.0 (additionally) 22.
  - Per DSA, R6s / 4.1 only / 4.1 + 4.0: CS 10/6/4, AB 4/2/2, TAB 4/2/2, IAV 8/8/0, MD 5/2/3, IG 5/2/3,
    MV 3/1/2, END 7/4/3, IIM 8/5/3. Equal to the nine-DSA table in the remapcap-design-modules README.
- **Perturbation (2026-11-14, not kept):** removing the transition sentence from the Core 4.1 7.6.2
  facts makes VT1 fire 0 times. The 22 "4.1 + 4.0" rows become "4.1". 54 statements stay affected,
  because the 7.6.1 and 7.6.2 texts changed anyway.
- Each run takes under 1 s.

## Limits
- The statements take step 1's relation labels (refers_to, version_scoped) and its sentence split as
  given. They are not rebuilt by rules.
- Section identity across versions is by layer and number (rule I1), as in script 07. A section that is
  renumbered between versions would show up as new + removed, not as changed. This did not happen for
  Core 4.0 → 4.1: the only differences in the section lists are 7.6.3 and 7.6.4, new in 4.1.
- "Affected" means that an input text differs. Whether the difference matters for a given statement
  (for example, a reworded sentence elsewhere in the section the statement points at) is a reading, not a
  rule.
