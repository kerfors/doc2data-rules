"""SSSOM TSV (metadata in '#' lines, YAML) -> RDF, one owl:Axiom per mapping record, in the form the
m11-rdf mapping set uses: owl:annotatedSource / annotatedProperty / annotatedTarget + sssom: slots.
Written as TriG into one named graph, because rulerun.py matches named graphs only.
Extension slots declared in the metadata (`extension_definitions`: slot_name, property as a CURIE of the curie_map)
are carried as literals under their property.
Run: python3 sssom_rdf.py <in.sssom.tsv> <out.trig> <graph IRI>"""
import sys

import pandas as pd
import rdflib
import yaml
from rdflib.namespace import OWL, RDF

SSSOM = rdflib.Namespace("https://w3id.org/sssom/")
IRI_SLOTS = {"mapping_justification", "reviewer_id", "author_id"}
LITERAL_SLOTS = {"subject_label", "object_label", "author_label", "comment", "predicate_modifier", "match_string"}

src, out, graph = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(src, encoding="utf-8").read().splitlines()
meta = yaml.safe_load("\n".join(l[1:] for l in lines if l.startswith("#")))
prefixes = meta["curie_map"]
df = pd.read_csv(src, sep="\t", comment="#", dtype=str, keep_default_na=False)


def expand(curie):
    p, local = curie.split(":", 1)
    return rdflib.URIRef(prefixes[p] + local)


EXT = {d["slot_name"]: expand(d["property"]) for d in meta.get("extension_definitions", [])}

ds = rdflib.Dataset()
g = ds.graph(rdflib.URIRef(graph))
for p, ns in prefixes.items():
    g.bind(p, ns)
g.bind("sssom", SSSOM)
g.bind("owl", OWL)
ms = rdflib.URIRef(meta["mapping_set_id"])
g.add((ms, RDF.type, SSSOM.MappingSet))
for k in ("mapping_set_title", "object_source_version"):
    g.add((ms, SSSOM[k], rdflib.Literal(meta[k])))
for _, r in df.iterrows():
    a = expand(r["record_id"])
    g.add((a, RDF.type, OWL.Axiom))
    g.add((a, OWL.annotatedSource, expand(r["subject_id"])))
    g.add((a, OWL.annotatedProperty, expand(r["predicate_id"])))
    g.add((a, OWL.annotatedTarget, expand(r["object_id"])))
    g.add((a, SSSOM.mapping_set, ms))
    for k in IRI_SLOTS & set(df.columns):
        if r[k]:
            g.add((a, SSSOM[k], expand(r[k])))
    for k in LITERAL_SLOTS & set(df.columns):
        if r[k]:
            g.add((a, SSSOM[k], rdflib.Literal(r[k])))
    for k, prop in EXT.items():
        if r[k]:
            g.add((a, prop, rdflib.Literal(r[k])))
ds.serialize(out, format="trig")
print(f"{len(df)} mapping records -> {out} graph <{graph}> ({len(g)} triples)")
