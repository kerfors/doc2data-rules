"""Checks on the LZZT stage 1 + 2a USDM build (out/usdm.ttl: objectives, title, endpoints), each failing the run:
  shape       SHACL with usdm-rdf (ontology, shapes, CT shapes; output graph only, no inference): conforms, 0 results
  ct          every Code: code and decode in the pinned DDF CT package under its mapping row's codelist, and its
              codeSystemVersion is that package's date
  mention     every endpoint row's subject_mention is printed in its subject sentence
  owner       every Endpoint sits in exactly one Objective
  provenance  every output node derives from a transcript element or a mapping row (out/prov.ttl)
  coverage    the printed elements of both transcripts that no rule used are the expected ones
  counts      6 Objectives, 1 StudyTitle, 5 Endpoints (2 Primary, 3 Secondary), 12 Codes, 11 names and 5 purposes not stated

Usage: python3 check.py   (from tests/lzzt-endpoints, after rulerun.py)
"""
import sys
from pathlib import Path

import pandas as pd
import pyshacl
import rdflib

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "machinery"))
import d2d_check  # noqa: E402

U = rdflib.Namespace("https://w3id.org/cdisc/usdm/v4/")
JT = rdflib.Namespace("urn:jt:rule-vocab:")
OWL = rdflib.OWL
SSSOM = rdflib.Namespace("https://w3id.org/sssom/")
CT_VERSION = "2026-09-25"
CT_FILE = "../lzzt-usdm/inputs/downloaded/DDF_Terminology_2026-09-25.txt"
RDF_IN = "../lzzt-usdm/inputs/usdm-rdf/"
NOT_STATED = "https://kerfors.github.io/soa2usdm/not-stated-in-protocol"
TRANSCRIPTS = ["../lzzt-layer1/transcript.trig", "transcript.trig"]
EXPECTED_UNUSED = {"p1.notice", "p1.compound", "p1.protocol", "s2", "s2.1.lead", "s2.2.lead",
                   "s3.9.1.2", "s3.9.1.2.sent.1", "s3.9.1.2.sent.4", "s3.9.1.2.sent.5", "s3.9.1.2.sent.6",
                   "s3.9.1.2.sent.7"}


def not_stated(g, node, prop, attr):
    return sum(1 for ea in g.objects(node, prop) if str(g.value(ea, U["ExtensionAttribute-url"])) == NOT_STATED
               and str(g.value(ea, U["ExtensionAttribute-valueString"])) == attr)


def main():
    out = rdflib.Graph().parse("out/usdm.ttl")
    prov = rdflib.Graph().parse("out/prov.ttl")
    mu = rdflib.Graph()
    for f in ("out/lv.trig", "out/ti.trig", "out/el.trig", "out/eo.trig"):
        ds = rdflib.Dataset()
        ds.parse(f, format="trig")
        for g in ds.graphs():
            mu += g

    shapes = rdflib.Graph()
    for f in ("usdm_v4.shapes.ttl", "usdm_v4.shapes-ct.ttl"):
        shapes.parse(RDF_IN + f)
    conforms, rg, _ = pyshacl.validate(out, shacl_graph=shapes, ont_graph=rdflib.Graph().parse(RDF_IN + "usdm_v4.ttl"),
                                       inference="none")
    results = len(list(rg.subjects(rdflib.RDF.type, rdflib.URIRef("http://www.w3.org/ns/shacl#ValidationResult"))))
    print(f"shape: conforms {conforms} | results {results}")
    assert conforms and results == 0, "SHACL"

    ct = pd.read_csv(CT_FILE, sep="\t", dtype=str, keep_default_na=False)
    members = set(zip(ct["Codelist Code"], ct["Code"], ct["CDISC Submission Value"]))
    codes = sorted(out.subjects(rdflib.RDF.type, U.Code))
    ok = 0
    for c in codes:
        rows = [x for x in prov.objects(c, JT.derivedFrom) if (x, JT.objectCodelist, None) in mu]
        assert len(rows) == 1, f"{c}: derives from {len(rows)} mapping rows with a codelist"
        key = (str(mu.value(rows[0], JT.objectCodelist)), str(out.value(c, U["Code-code"])),
               str(out.value(c, U["Code-decode"])))
        if key in members and str(out.value(c, U["Code-codeSystemVersion"])) == CT_VERSION:
            ok += 1
        else:
            print(f"  not in the package: {c} {key}")
    print(f"ct: {ok} of {len(codes)} Codes in DDF Terminology {CT_VERSION} (code, decode, codelist, version)")
    assert ok == len(codes), "CT"

    t = d2d_check.Transcripts(TRANSCRIPTS)
    rows = list(mu.subjects(JT.subjectMention, None))
    bad = [r for r in rows if str(mu.value(r, JT.subjectMention)) not in t.name(mu.value(r, OWL.annotatedSource))]
    print(f"mention: {len(rows)} endpoint rows | subject_mention not printed in its sentence {len(bad)}")
    assert not bad, "mention"

    eps = sorted(out.subjects(rdflib.RDF.type, U.Endpoint))
    owners = [len(list(out.subjects(U["Objective-endpoints"], e))) for e in eps]
    print(f"owner: {len(eps)} Endpoints | in exactly one Objective {owners.count(1)}")
    assert owners.count(1) == len(eps), "owner"

    nodes = set(out.subjects(rdflib.RDF.type, None))
    no_prov = [n for n in nodes if (n, JT.derivedFrom, None) not in prov]
    print(f"provenance: {len(nodes)} output nodes | without jt:derivedFrom {len(no_prov)}")
    assert not no_prov, "provenance"

    used = set(prov.objects(None, JT.derivedFrom))
    printed, unused = 0, set()
    for tg in t.graphs:
        for e in t.elements(tg):
            if t.printed(e):
                printed += 1
                if e not in used:
                    unused.add(str(t.u.value(e, d2d_check.D2D.localId)))
    print(f"coverage: {printed} printed elements | used {printed - len(unused)} | not used {len(unused)}: "
          + ", ".join(sorted(unused)))
    assert unused == EXPECTED_UNUSED, "coverage"

    objs = list(out.subjects(rdflib.RDF.type, U.Objective))
    titles = list(out.subjects(rdflib.RDF.type, U.StudyTitle))
    lv = pd.Series([str(out.value(out.value(e, U["Endpoint-level"]), U["Code-decode"])) for e in eps]).value_counts()
    names = sum(not_stated(out, o, U["Objective-extensionAttributes"], "name") for o in objs) + \
        sum(not_stated(out, e, U["Endpoint-extensionAttributes"], "name") for e in eps)
    purposes = sum(not_stated(out, e, U["Endpoint-extensionAttributes"], "purpose") for e in eps)
    print(f"counts: Objectives {len(objs)} | StudyTitles {len(titles)} | Endpoints {len(eps)} "
          f"({', '.join(f'{k} {v}' for k, v in sorted(lv.items()))}) | Codes {len(codes)} | "
          f"not stated: name {names}, purpose {purposes}")
    assert (len(objs), len(titles), len(eps), lv.get("Primary Endpoint"), lv.get("Secondary Endpoint"), len(codes),
            names, purposes) == (6, 1, 5, 2, 3, 12, 11, 5), "counts"


if __name__ == "__main__":
    main()
