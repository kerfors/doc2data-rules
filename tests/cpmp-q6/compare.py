"""Compare the rule output with what 01_build_modules.py wrote into the OWL modules, row by row."""
import glob
import rdflib
from urllib.parse import unquote

CP = "https://kerfors.github.io/early-clinical-design-research/cpmp-design-modules/"
py = rdflib.Graph()
for f in glob.glob("inputs/cpmp-design-modules/modules/*.ttl"):
    py.parse(f)

q_py = f"""PREFIX cpmp:<{CP}> PREFIX owl:<http://www.w3.org/2002/07/owl#> PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>
SELECT ?isa ?act ?vis ?alloc ?text WHERE {{
  {{ ?ax owl:annotatedSource ?d ; owl:annotatedProperty rdfs:subClassOf ; owl:annotatedTarget ?r ; cpmp:allocation ?alloc .
     FILTER(?alloc IN ("default", "default assumed, no document"))
     ?r owl:someValuesFrom ?cell . ?cell cpmp:activityKey ?act ; cpmp:visit ?vis . BIND("" AS ?text) }}
  UNION
  {{ ?ax owl:annotatedSource ?d ; owl:annotatedProperty cpmp:overrides ; owl:annotatedTarget ?t ; cpmp:evidenceText ?text .
     OPTIONAL {{ ?t cpmp:activityKey ?ca ; cpmp:visit ?cv }}
     OPTIONAL {{ ?ax cpmp:activityKey ?aa ; cpmp:visit ?av }}
     BIND(COALESCE(?ca, ?aa) AS ?act) BIND(COALESCE(?cv, ?av) AS ?vis)
     BIND(IF(BOUND(?ca), "overrides", "overrides (activity not in master SoA)") AS ?alloc) }}
  BIND(STRAFTER(STR(?d), "ISA_") AS ?isa)
}}"""
py_rows = {(str(r.isa), str(r.act), str(r.vis), str(r.alloc), str(r.text)) for r in py.query(q_py)}

out = rdflib.Graph().parse("out/q6_allocations.ttl")
facts = rdflib.Dataset(); facts.parse("facts.trig", format="trig")
fg = facts.graph(rdflib.URIRef("urn:q6:g:facts"))
F = rdflib.Namespace("urn:q6:fact-vocab:"); Q = rdflib.Namespace("urn:q6:vocab:")
MAP = {"takes (silent)": "default", "takes (restated)": "restated"}   # Python's labels for the same decisions
rule_rows = set()
for a in out.subjects(rdflib.RDF.type, Q.Allocation):
    isa = str(fg.value(out.value(a, Q.isa), F.code))
    tgt = out.value(a, Q.target)
    alloc = str(out.value(a, Q.allocation))
    if fg.value(tgt, F.activity) is not None:
        act, vis = str(fg.value(tgt, F.activity)), str(fg.value(tgt, F.visit))
    else:
        act, vis = str(out.value(a, Q.activity)), "ED"
    rule_rows.add((isa, act, vis, MAP.get(alloc, alloc), str(out.value(a, Q.evidenceText) or "")))

print(f"Python build: {len(py_rows)} rows | rules: {len(rule_rows)} rows | identical: {len(py_rows & rule_rows)}")
for r in sorted(py_rows - rule_rows): print("  only in Python:", r)
for r in sorted(rule_rows - py_rows): print("  only in rules: ", r)
from collections import Counter
print("by allocation:", dict(Counter(r[3] for r in rule_rows)))
