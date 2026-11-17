# Test: CPMP Q6 (master defaults: take, override, silent) as rules

Rebuilds the schedule-default decisions of early-clinical-design-research
`cpmp-design-modules/scripts/01_build_modules.py` (read at 8c374cc), the CPMP answer to competency
question Q6 "Which defaults does a child take, override or stay silent on?".

## Inputs (`inputs/`, sha256 in `inputs/MANIFEST.sha256`; all from early-clinical-design-research 8c374cc)
- `cpmp-soa-join/output/layered_grid.csv` — read WITHOUT its computed `kind` column.
- `cpmp-design-modules/sources/soa_statements.csv` — override statements with text.
- `cpmp-design-modules/sources/ctgov/*.json` — CT.gov records of the three ISAs with no documents.
- `cpmp-design-modules/modules/*.ttl` — the Python build's OWL modules, used only by the comparison.

## Files
- `build_facts.py` → `facts.trig` (4713 facts). Transcription only.
- `rules_q6.trig` — D1 master default; D2 override on a master default; D3 override on an activity not in
  the master SoA (→ disease-state design); D4 takes, restated; D5 takes, silent; D6 default assumed
  (no document). Each rule carries the status label of its output.
- `compare.py` — row by row against the allocations and overrides written into the OWL modules.
- `out/` — `q6_allocations.ttl`, `prov.ttl`, `firings.ttl`, `compiled.rq`.

## Run
```
python3 build_facts.py
python3 ../../machinery/rulerun.py --rules rules_q6.trig --facts facts.trig --out out --output q6_allocations.ttl --firing-ns urn:q6:firing:
python3 compare.py
```

## Result (2026-11-13, re-run 2026-11-14 with the shared compiler)
48 rows from the rules, 48 from the Python build, 48 identical (ISA, activity, visit, allocation, evidence
sentence); master defaults identical (NRS for pain, PGI, Rescue medication usage reporting at ED).
27 takes silently, 9 overrides, 9 default assumed, 3 overrides → disease state. D4 fires 0 times.
Perturbation (2026-11-13): removing OA01's NRS override statement turns that cell into "takes (silent)".
