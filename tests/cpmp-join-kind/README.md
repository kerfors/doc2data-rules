# Test: CPMP SoA join 'kind' classification as rules

Rebuilds the cell classification of early-clinical-design-research `cpmp-soa-join/cpmp_soa_join.ipynb`
(read at 8c374cc): every ISA × activity key × visit cell as inherited / restated / added / extended /
isa_only / isa_only_extended / override_ed, plus the delegated and addition flags.

## Inputs (`inputs/`, sha256 in `inputs/MANIFEST.sha256`)
- `soa2usdm-collections-cpmp/` — soa2usdm-collections at cf9541d, `collections/cpmp`: 13 consolidated JSON
  and `studies_protocols.xlsx` (the notebook's own inputs). Public.
- `cpmp-soa-join/activity_crosswalk.csv` — the join's crosswalk (mapping data, as decided in that repo). Read by
  `crosswalk_sssom.py` and by `compare_kind.py`.
- `cpmp-soa-join/output/layered_grid.csv` — the join's result, used only by the comparison.

## Files
- `build_facts_kind.py` → `facts.trig` (5962 facts). Transcription only.
- `crosswalk_sssom.py` → `crosswalk.sssom.tsv` — the crosswalk as an SSSOM mapping set, content unchanged: 89
  records, one per printed name (as decided upstream), subject = the name as printed, object = its activity key.
  skos:exactMatch 80; skos:broadMatch 3 (the printed name adds a qualifier or a compound: C-SSRS Since Last Visit,
  ECG (single), LY3857210 PK sample); kept apart 6, object `sssom:NoTermFound` (no key in the crosswalk, so the key is
  the name itself; the name it was kept apart from stays in `comment`, so there is no object for a `Not` row).
  semapv:LexicalMatching for the 67 identical names, semapv:ManualMappingCuration for the 22 proposed; no
  reviewer_id, since nothing is decided. `basis` is an extension slot (`jt:basis`). `run_all.sh` checks that the
  script reproduces the committed TSV; `sssom_rdf.py` turns it into the graph `urn:k:g:crosswalk`.
- `rules_kind.trig` — 22 rules: K1-K2 key via crosswalk; K3-K6 master cells, master keys, master visits,
  ISA cells; S1-S4 the four statement patterns; C1-C7 the seven kinds (override wins by negative
  condition); F1-F2 flags; ST1-ST3 status labels (see below).
- `compare_kind.py` — row by row against `layered_grid.csv`.
- `out/` — `kind_cells.ttl` (result), `prov.ttl`, `firings.ttl`, `compiled.rq` (the generated SPARQL),
  `crosswalk.trig` (the mapping set as rule input).

## Run
```
mkdir -p out
python3 ../../machinery/sssom_rdf.py crosswalk.sssom.tsv out/crosswalk.trig urn:k:g:crosswalk
python3 build_facts_kind.py
python3 ../../machinery/rulerun.py --rules rules_kind.trig --facts facts.trig out/crosswalk.trig --out out --output kind_cells.ttl --firing-ns urn:k:firing:
python3 compare_kind.py
```

## Result (2026-11-14)
2777 rows from the rules, 2777 in the join, 2777 identical on (ISA, activity key, visit, kind,
delegated_by_master, addition_stated). inherited 1773, isa_only 423, added 360, extended 139,
isa_only_extended 40, restated 30, override_ed 12; delegated cells 525; additions master + DSA 9,
master only 16. About 45 s.

## Status labels from mapping status (2026-11-14)
Rules ST1-ST3 label every cell by the status of the crosswalk entries its key rests on. They read the
provenance K1/K2 wrote (row key derivedFrom crosswalk entry):
- **ST1, ST2:** a cell whose key came, in its own ISA (ST1) or in the master (ST2), through an entry still
  `proposed` is "rule-derived from analyst readings". Proposed = a ManualMappingCuration record with no
  reviewer_id;
- **ST3:** every other cell is "rule-derived".
The labels are those of early-clinical-design-research `competency-questions` (`STATUS_ORDER`). Deciding
an entry is a change to the mapping data only; the rules do not change. (Upstream status "decided" has no
record yet: `crosswalk_sssom.py` stops at it, and it then needs a reviewer_id to carry.)

Result: 469 cells "rule-derived from analyst readings", 2308 "rule-derived". `compare_kind.py` checks every
label against an independent pandas reading of the same inputs: 2777/2777 identical. By kind: inherited 285,
isa_only 107, extended 49, added 15, isa_only_extended 7, restated 3, override_ed 3. 21 of the 22 proposed
entries carry cells. The most-used are "Concomitant medications" (108 cells) and "AEs" (97). "Dispense…",
"Study Intervention IV infusion" and "WOMAC®" carry 1-4 each. "Participant Devices" carries none.

Perturbation (not kept): setting "Concomitant medications" to decided turns exactly its 108 cells into
"rule-derived" (469 → 361).

Limit: the label follows positive dependencies only. A kept-apart entry (`use = no`, still proposed) labels
the cells of its own key. It does not label the cells of the key it might have merged into: that key is not
in the crosswalk.

