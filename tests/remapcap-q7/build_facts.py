"""Transcription step for the Q7 rule test (REMAP-CAP Core 4.0 -> 4.1). No decisions here.

Reads the pinned inputs and writes:
  facts.trig          graph urn:q7:g:facts        DSA -> Core / PANDA / SAA statements (step 1, not mention_only),
                                                  documents with header version and date, PANDA and Core 4.0 sections
  facts_core41.trig   graph urn:q7:g:facts-core41 Core 4.1 document and sections (the new parent version)
  mapping.trig        graph urn:jt:g:topic-rules  topic_rules.csv as mapping data (pattern -> target section)

The statements carry step 1's relation label (refers_to / version_scoped) as given, as cpmp-q6 takes the
join's cells. Section text is the step 1 text layer as printed (not redistributed, see README).
Run from this folder.
"""
from urllib.parse import quote

import pandas as pd
import rdflib
from rdflib import Literal, Namespace, RDF, URIRef, XSD

ECDR = "inputs/ecdr-8c374cc/remapcap-design-modules"
F = Namespace("urn:q7:fact-vocab:")
M = Namespace("urn:q7:map-vocab:")
D = "urn:q7:fact:"

xr = pd.read_csv(f"{ECDR}/output/step1/cross_references.csv", dtype=str, keep_default_na=False)
docs = pd.read_csv(f"{ECDR}/output/documents.csv", dtype=str, keep_default_na=False)
sections = pd.read_csv("inputs/not-redistributed/sections.csv", dtype=str, keep_default_na=False)
topic = pd.read_csv(f"{ECDR}/sources/topic_rules.csv", dtype=str, keep_default_na=False)


def doc_iri(key):
    return URIRef(D + "doc/" + key)


def add_doc(g, r):
    d = doc_iri(r.key)
    g.add((d, RDF.type, F.Document))
    g.add((d, F.key, Literal(r.key)))
    g.add((d, F.layer, Literal(r.layer)))
    g.add((d, F.headerName, Literal(r.header_name)))
    g.add((d, F.version, Literal(r.version)))
    g.add((d, F.date, Literal(r.date, datatype=XSD.date)))


def add_sections(g, key):
    rows = sections[sections.doc == key]
    assert len(rows) > 0, f"no sections for {key}"
    assert not rows.number.duplicated().any(), f"{key}: duplicate section numbers"
    for r in rows.itertuples():
        s = URIRef(D + "section/" + key + "/" + quote(r.number, safe=""))
        g.add((s, RDF.type, F.Section))
        g.add((s, F.doc, doc_iri(key)))
        g.add((s, F.number, Literal(r.number)))
        g.add((s, F.title, Literal(r.title)))
        g.add((s, F.text, Literal(r.text)))
    return len(rows)


ds = rdflib.Dataset()
g = ds.graph(URIRef("urn:q7:g:facts"))
for r in docs[docs.key != "CORE41"].itertuples():
    add_doc(g, r)
n_sec = {k: add_sections(g, k) for k in ["CORE40", "PANDA"]}

stm = xr[(xr.layer == "DSA") & xr.target.isin(["CORE", "PANDA", "SAA"]) & (xr.relation != "mention_only")]
assert not stm.duplicated(["doc", "section", "sentence"]).any(), "statement key (doc, section, sentence) not unique"
for (doc, sec), grp in stm.groupby(["doc", "section"], sort=False):
    for k, r in enumerate(grp.itertuples()):
        sid = f"{doc}/{sec}/{k}"
        s = URIRef(D + "stmt/" + quote(sid, safe="/"))
        g.add((s, RDF.type, F.Statement))
        g.add((s, F.id, Literal(sid)))
        g.add((s, F.doc, doc_iri(doc)))
        g.add((s, F.section, Literal(sec)))
        g.add((s, F.target, Literal(r.target)))
        g.add((s, F.relation, Literal(r.relation)))
        g.add((s, F.sentence, Literal(r.sentence)))
ds.serialize("facts.trig", format="trig")

ds41 = rdflib.Dataset()
g41 = ds41.graph(URIRef("urn:q7:g:facts-core41"))
add_doc(g41, next(docs[docs.key == "CORE41"].itertuples()))
n_sec["CORE41"] = add_sections(g41, "CORE41")
ds41.serialize("facts_core41.trig", format="trig")

dm = rdflib.Dataset()
gm = dm.graph(URIRef("urn:jt:g:topic-rules"))
for r in topic.itertuples():
    t = URIRef(f"urn:q7:map:topic-rule/{r.order}")
    gm.add((t, RDF.type, M.TopicRule))
    gm.add((t, M.order, Literal(int(r.order))))
    gm.add((t, M.pattern, Literal(r.pattern)))
    gm.add((t, M.source, Literal(r.source)))
    if r.title_term:
        gm.add((t, M.titleTerm, Literal(r.title_term)))
    for target in r.targets.split(";"):
        layer, number = target.split(" ")
        gm.add((t, M.target, URIRef(f"urn:q7:sec:{layer}/{quote(number, safe='')}")))
dm.serialize("mapping.trig", format="trig")

print(f"facts: {len(g)} triples; {len(stm)} statements "
      f"({stm.target.value_counts().to_dict()}; {stm.relation.value_counts().to_dict()}); "
      f"documents {len(docs) - 1}; sections {n_sec['CORE40']} Core 4.0, {n_sec['PANDA']} PANDA")
print(f"facts_core41: {len(g41)} triples; sections {n_sec['CORE41']} Core 4.1")
print(f"mapping: {len(gm)} triples; {len(topic)} topic rules")
