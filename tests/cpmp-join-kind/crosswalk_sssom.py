"""The join's activity crosswalk (pinned CSV, early-clinical-design-research 8c374cc) as an SSSOM mapping set.

Format only, content unchanged: one record per CSV row, in CSV order. The crosswalk is decided upstream; this
script is the only way the TSV is made, and run_all.sh checks that it reproduces the committed crosswalk.sssom.tsv.
- subject = the name as printed, object = the activity key (both as minted IRIs, with their text as label);
- predicate by basis: skos:broadMatch where the printed name adds a qualifier or a compound to its key, else
  skos:exactMatch; a kept-apart name has no key in the crosswalk: object sssom:NoTermFound (its key is itself);
- justification: semapv:LexicalMatching for identical names, semapv:ManualMappingCuration for the others;
- no reviewer_id: no entry is decided (proposed = no reviewer, as in every mapping set here);
- basis is carried as the extension slot `basis` (jt:basis), comment as is.
Run from tests/cpmp-join-kind: python3 crosswalk_sssom.py <out.sssom.tsv>
"""
import sys
from urllib.parse import quote

import pandas as pd
import yaml

SRC = "inputs/cpmp-soa-join/activity_crosswalk.csv"
EXACT = {"identical", "case_typography", "abbreviation_or_plural", "document_supported"}
BROAD = {"qualifier_added", "compound_named"}

xw = pd.read_csv(SRC, dtype=str, keep_default_na=False)
assert list(xw.columns) == ["name_as_printed", "activity_key", "basis", "use", "status", "comment"], list(xw.columns)
assert xw.name_as_printed.is_unique
assert set(xw.basis) == EXACT | BROAD | {"kept_apart"}, set(xw.basis)
kept = xw.basis == "kept_apart"
assert ((xw.use == "no") == kept).all()
assert (xw.activity_key[kept] == xw.name_as_printed[kept]).all()
assert ((xw.status == "n/a") == (xw.basis == "identical")).all()
assert ((xw.status == "proposed") == (xw.basis != "identical")).all()

meta = {
    "curie_map": {
        "xw": "urn:k:crosswalk:",
        "kn": "urn:k:name:",
        "kk": "urn:k:key:",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "semapv": "https://w3id.org/semapv/vocab/",
        "sssom": "https://w3id.org/sssom/",
        "jt": "urn:jt:rule-vocab:",
    },
    "mapping_set_id": "urn:k:mapping-set:crosswalk",
    "mapping_set_title": "CPMP SoA join activity crosswalk (name as printed -> activity key)",
    "mapping_set_description": "Made by crosswalk_sssom.py from early-clinical-design-research 8c374cc "
                               "cpmp-soa-join/activity_crosswalk.csv; content unchanged.",
    "license": "https://opensource.org/licenses/MIT",
    "object_source_version": "early-clinical-design-research 8c374cc",
    "extension_definitions": [{"slot_name": "basis", "property": "jt:basis", "type_hint": "xsd:string"}],
}

rows = []
for k, r in enumerate(xw.itertuples(), start=1):
    rows.append({
        "record_id": f"xw:{k}",
        "subject_id": "kn:" + quote(r.name_as_printed, safe=""),
        "subject_label": r.name_as_printed,
        "predicate_id": "skos:broadMatch" if r.basis in BROAD else "skos:exactMatch",
        "object_id": "sssom:NoTermFound" if r.basis == "kept_apart" else "kk:" + quote(r.activity_key, safe=""),
        "object_label": "" if r.basis == "kept_apart" else r.activity_key,
        "mapping_justification": "semapv:LexicalMatching" if r.basis == "identical" else "semapv:ManualMappingCuration",
        "comment": r.comment,
        "basis": r.basis,
    })

header = "".join("#" + l + "\n" for l in yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).splitlines())
with open(sys.argv[1], "w", encoding="utf-8", newline="") as fh:
    fh.write(header)
    pd.DataFrame(rows).to_csv(fh, sep="\t", index=False, lineterminator="\n")
print(f"{len(rows)} records -> {sys.argv[1]} (exactMatch {sum(r['predicate_id'] == 'skos:exactMatch' for r in rows)}, "
      f"broadMatch {sum(r['predicate_id'] == 'skos:broadMatch' for r in rows)}, "
      f"NoTermFound {sum(r['object_id'] == 'sssom:NoTermFound' for r in rows)}, "
      f"ManualMappingCuration {sum(r['mapping_justification'] == 'semapv:ManualMappingCuration' for r in rows)})")
