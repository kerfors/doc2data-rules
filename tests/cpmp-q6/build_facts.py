"""Transcription step for the Q6 rule test: read the same inputs the Python build reads and write them
as plain facts (TriG). No decisions here. The join's computed 'kind' column is deliberately not read.
Run from /tmp/jt/q6 with the early-clinical-design-research clone at ../ecdr.
"""
import json
import re
from urllib.parse import quote

import pandas as pd
import rdflib
from rdflib import Literal, Namespace, RDF, URIRef

ECDR = "inputs"
F = Namespace("urn:q6:fact-vocab:")
D = "urn:q6:fact:"

grid = pd.read_csv(f"{ECDR}/cpmp-soa-join/output/layered_grid.csv",
                   usecols=["isa", "nct_id", "compound", "disease", "activity_key", "visit",
                            "master_mark", "isa_mark"])
stm = pd.read_csv(f"{ECDR}/cpmp-design-modules/sources/soa_statements.csv").fillna("")

ds = rdflib.Dataset()
g = ds.graph(URIRef("urn:q6:g:facts"))


def cell(activity, visit):
    return URIRef(D + "cell/" + quote(activity, safe="") + "/" + visit)


# Master cells: cells the master SoA marks (as the join reports them).
for (a, v), _ in grid[grid["master_mark"]].groupby(["activity_key", "visit"]):
    c = cell(a, v)
    g.add((c, RDF.type, F.MasterCell))
    g.add((c, F.activity, Literal(a)))
    g.add((c, F.visit, Literal(v)))
    g.add((c, F.key, Literal(f"{a}|{v}")))

# Documented ISAs and the cells each ISA's own SoA marks.
for (isa, nct, comp, dis), _ in grid.groupby(["isa", "nct_id", "compound", "disease"]):
    i = URIRef(D + "isa/" + isa)
    g.add((i, RDF.type, F.DocumentedISA))
    g.add((i, F.code, Literal(isa)))
    g.add((i, F.nct, Literal(nct)))
    g.add((i, F.compound, Literal(comp)))
    g.add((i, F.disease, Literal(dis)))
for r in grid[grid["isa_mark"]].itertuples():
    m = URIRef(D + "mark/" + r.isa + "/" + quote(r.activity_key, safe="") + "/" + r.visit)
    g.add((m, RDF.type, F.IsaMark))
    g.add((m, F.isa, URIRef(D + "isa/" + r.isa)))
    g.add((m, F.activity, Literal(r.activity_key)))
    g.add((m, F.visit, Literal(r.visit)))

# SoA statements of kind override_ed, with their text.
for k, r in enumerate(stm[stm["statement_kind"] == "override_ed"].itertuples()):
    s = URIRef(D + f"stmt/{k}")
    g.add((s, RDF.type, F.OverrideStatement))
    g.add((s, F.nct, Literal(r.nct_id)))
    g.add((s, F.activity, Literal(r.activity_key)))
    g.add((s, F.text, Literal(r.text)))
    g.add((s, F.id, Literal(f"s{k}")))

# Registered ISAs with no documents: same CT.gov reading as 01_build_modules.py.
from pathlib import Path
for f in sorted(Path(f"{ECDR}/cpmp-design-modules/sources/ctgov").glob("NCT*.json")):
    p = json.loads(f.read_text())["protocolSection"]
    ident = p["identificationModule"]
    secondary = [s["id"] for s in ident.get("secondaryIdInfos", [])]
    assert "H0P-MC-CPMP" in secondary, f.name
    (study,) = [s for s in secondary if s.startswith("H0P-MC-") and s != "H0P-MC-CPMP"]
    code = study.replace("H0P-MC-", "")
    (dis,) = set(re.findall(r"\((OA|CLBP|DPNP)\)", " ".join(p["descriptionModule"]["briefSummary"].split())))
    i = URIRef(D + "isa/" + code)
    g.add((i, RDF.type, F.RegisteredISANoDocuments))
    g.add((i, F.code, Literal(code)))
    g.add((i, F.nct, Literal(ident["nctId"])))
    g.add((i, F.disease, Literal(dis)))

# Disease-state designs (not public), one per disease.
for dis in ["OA", "CLBP", "DPNP"]:
    x = URIRef(D + "disease/" + dis)
    g.add((x, RDF.type, F.DiseaseStateDesign))
    g.add((x, F.disease, Literal(dis)))
    g.add((x, F.contentStatus, Literal("not public")))

ds.serialize("facts.trig", format="trig")
print(len(g), "facts:",
      {str(t).split(":")[-1]: len(set(g.subjects(RDF.type, t))) for t in set(g.objects(None, RDF.type))})
