"""Compare the rule output with the join's layered_grid.csv, row by row:
(isa, activity_key, visit, kind, delegated_by_master, addition_stated)."""
from collections import Counter

import pandas as pd
import rdflib

grid = pd.read_csv("inputs/cpmp-soa-join/output/layered_grid.csv").fillna("")
nct_isa = dict(zip(grid["nct_id"], grid["isa"]))
py = {(r.isa, r.activity_key, r.visit, r.kind, bool(r.delegated_by_master), str(r.addition_stated))
      for r in grid.itertuples()}

out = rdflib.Graph().parse("out/kind_cells.ttl")
facts = rdflib.Dataset(); facts.parse("facts.trig", format="trig")
fg = facts.graph(rdflib.URIRef("urn:k:g:facts"))
K = rdflib.Namespace("urn:k:vocab:"); F = rdflib.Namespace("urn:k:fact-vocab:")
rules = set()
for c in out.subjects(rdflib.RDF.type, K.Cell):
    nct = str(fg.value(out.value(c, K.doc), F.nct))
    rules.add((nct_isa[nct], str(out.value(c, K.key)), str(out.value(c, K.visit)), str(out.value(c, K.kind)),
               out.value(c, K.delegatedByMaster) is not None, str(out.value(c, K.additionStated) or "")))

print(f"join: {len(py)} rows | rules: {len(rules)} rows | identical: {len(py & rules)}")
for r in sorted(py - rules)[:20]:
    print("  only in join: ", r)
for r in sorted(rules - py)[:20]:
    print("  only in rules:", r)
print("kinds (rules):", dict(Counter(r[3] for r in rules)))
print("delegated cells:", sum(r[4] for r in rules), "| addition_stated:", dict(Counter(r[5] for r in rules if r[5])))

# Status labels (rules ST1-ST3) against an independent pandas reading of the same inputs: a cell is
# "rule-derived from analyst readings" when its key, in its own ISA or in the master, came through a
# crosswalk entry whose status is still 'proposed'.
import json
xw = pd.read_csv("inputs/cpmp-soa-join/activity_crosswalk.csv", dtype=str).fillna("")
xw["key"] = xw["activity_key"].where(xw["use"] == "yes", xw["name_as_printed"])
entry = {r.name_as_printed: r for r in xw.itertuples()}
studies = pd.read_excel("inputs/soa2usdm-collections-cpmp/studies_protocols.xlsx", sheet_name="studies")
master = studies[studies.cpmp_layer == "master"].nct_id.item()
proposed = {}
for nct in studies.nct_id:
    d = json.load(open(f"inputs/soa2usdm-collections-cpmp/{nct}_consolidated.json", encoding="utf-8"))
    proposed[nct] = {entry[a["activity_name"]].key for a in d["unified_activities"]
                     if not a["is_section_header"] and entry[a["activity_name"]].status == "proposed"}
py_status = {}
for r in grid.itertuples():
    analyst = r.activity_key in proposed[r.nct_id] or r.activity_key in proposed[master]
    py_status[(r.isa, r.activity_key, r.visit)] = "rule-derived from analyst readings" if analyst else "rule-derived"
rule_status = {}
for c in out.subjects(rdflib.RDF.type, K.Cell):
    nct = str(fg.value(out.value(c, K.doc), F.nct))
    labels = {str(s) for s in out.objects(c, K.status)}
    assert len(labels) == 1, (nct, str(out.value(c, K.key)), labels)
    rule_status[(nct_isa[nct], str(out.value(c, K.key)), str(out.value(c, K.visit)))] = labels.pop()
same = sum(py_status[k] == rule_status.get(k) for k in py_status)
print(f"status: pandas {len(py_status)} | rules {len(rule_status)} | identical {same} | "
      f"{dict(Counter(rule_status.values()))}")
for k in sorted(k for k in py_status if py_status[k] != rule_status.get(k))[:20]:
    print("  status differs:", k, py_status[k], "|", rule_status.get(k))

assert py == rules, f"rows differ: {len(py - rules)} only in join, {len(rules - py)} only in rules"
assert py_status == rule_status, f"status differs: pandas {len(py_status)} | rules {len(rule_status)} | identical {same}"
