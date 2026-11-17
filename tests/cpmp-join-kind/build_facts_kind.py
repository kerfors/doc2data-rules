"""Transcription step for the CPMP join 'kind' rule test.

Reads the same inputs as early-clinical-design-research/cpmp-soa-join/cpmp_soa_join.ipynb
(soa2usdm-collections cpmp at cf9541d: consolidated JSON per protocol + studies_protocols.xlsx; and the
join's activity_crosswalk.csv) and writes them as plain facts. No decisions: visit numbers are read from the
printed visit header as the notebook does, activity names stay as printed, the crosswalk goes into its own
graph as mapping data.
Run from /tmp/jt/kind. Writes facts.trig.
"""
import json
import re
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import rdflib
from rdflib import Literal, Namespace, RDF, URIRef

SRC = Path("inputs/soa2usdm-collections-cpmp")
F = Namespace("urn:k:fact-vocab:")
D = "urn:k:fact:"
MASTER = "NCT05986292"
VISIT_NO = re.compile(r"^(V\s?\d+|ED)$")

ds = rdflib.Dataset()
g = ds.graph(URIRef("urn:k:g:facts"))
xg = ds.graph(URIRef("urn:k:g:crosswalk"))


def iri(*parts):
    return URIRef(D + "/".join(quote(str(p), safe="") for p in parts))


studies = pd.read_excel(SRC / "studies_protocols.xlsx", sheet_name="studies")
for r in studies.itertuples():
    doc = iri("doc", r.nct_id)
    g.add((doc, RDF.type, F.Document))
    g.add((doc, F.nct, Literal(r.nct_id)))
    g.add((doc, F.layer, Literal(r.cpmp_layer)))
    g.add((doc, F.studyCode, Literal(r.study_code)))
    if r.cpmp_layer == "ISA":
        g.add((doc, F.compound, Literal(r.compound)))
        g.add((doc, F.diseaseStateAddendum, Literal(r.disease_state_addendum)))

n_marks = n_notes = 0
for r in studies.itertuples():
    nct = r.nct_id
    d = json.load(open(SRC / f"{nct}_consolidated.json", encoding="utf-8"))
    assert list(d["timeline_segments"]) == ["main"], nct
    doc = iri("doc", nct)
    cols = {}
    for c in d["timeline_segments"]["main"]:
        vals = [p["value"].strip() for p in c["property_values"]
                if p["property_type"] == "visit" and VISIT_NO.match(p["value"].strip())]
        assert len(vals) == 1, (nct, c["composite_label"])
        v = vals[0].replace(" ", "")
        cols[c["xcol_id"]] = v
        col = iri("col", nct, v)
        g.add((col, RDF.type, F.VisitColumn))
        g.add((col, F.inDoc, doc))
        g.add((col, F.visit, Literal(v)))
    acts = {a["xact_id"]: a for a in d["unified_activities"]}
    for a in d["unified_activities"]:
        if a["is_section_header"]:
            continue
        row = iri("row", nct, a["xact_id"])
        g.add((row, RDF.type, F.ActivityRow))
        g.add((row, F.inDoc, doc))
        g.add((row, F.name, Literal(a["activity_name"])))
    for m in d["schedule_matrix"]:
        if not str(m["consolidated_value"]).strip():
            continue
        a = acts[m["xact_id"]]
        assert not a["is_section_header"]
        mk = iri("mark", nct, m["xact_id"], cols[m["xcol_id"]])
        g.add((mk, RDF.type, F.Mark))
        g.add((mk, F.row, iri("row", nct, m["xact_id"])))
        g.add((mk, F.visit, Literal(cols[m["xcol_id"]])))
        n_marks += 1
    for k, n in enumerate(d["unified_annotations"]):
        an = iri("note", nct, k)
        g.add((an, RDF.type, F.Annotation))
        g.add((an, F.inDoc, doc))
        g.add((an, F.id, Literal(f"{nct}-{k}")))
        g.add((an, F.text, Literal(n["annotation_text"])))
        for x in n["referenced_xacts"]:
            g.add((an, F.refersToRow, iri("row", nct, x)))
        n_notes += 1

# The join's activity crosswalk: mapping data, as decided in that repo (name as printed -> activity key).
xw = pd.read_csv(Path("inputs/cpmp-soa-join/activity_crosswalk.csv"), dtype=str).fillna("")
for k, r in enumerate(xw.itertuples()):
    e = iri("xw", k)
    xg.add((e, RDF.type, F.CrosswalkEntry))
    xg.add((e, F.nameAsPrinted, Literal(r.name_as_printed)))
    xg.add((e, F.activityKey, Literal(r.activity_key)))
    xg.add((e, F.use, Literal(r.use)))
    xg.add((e, F.status, Literal(r.status)))

ds.serialize("facts.trig", format="trig")
print(f"{len(g)} facts, {len(xg)} crosswalk triples; {len(studies)} documents, {n_marks} marks, {n_notes} annotations")
