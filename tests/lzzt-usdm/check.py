"""Checks on the LZZT stage-1 USDM build (out/usdm.ttl), each failing the run when it does not hold:
  shape       SHACL with usdm-rdf (ontology, shapes, CT shapes; output graph only, no inference): conforms, 0 results
  ct          every Code: its code and decode are in the pinned DDF CT package under the codelist its mapping row names,
              and its codeSystemVersion is that package's date
  provenance  every output node derives from the transcript or a mapping row (out/prov.ttl)
  coverage    the printed transcript elements no rule used are the expected ones
  counts      6 Objectives (2 Primary, 4 Secondary), 1 StudyTitle, 7 Codes, 6 names not stated

Usage: python3 check.py   (from tests/lzzt-usdm, after rulerun.py)
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
CT_VERSION = "2026-09-25"
CT_FILE = "inputs/downloaded/DDF_Terminology_2026-09-25.txt"
NOT_STATED = "https://kerfors.github.io/soa2usdm/not-stated-in-protocol"
EXPECTED_UNUSED = {"p1.notice", "p1.compound", "p1.protocol", "s2", "s2.1.lead", "s2.2.lead"}


def main():
    out = rdflib.Graph().parse("out/usdm.ttl")
    prov = rdflib.Graph().parse("out/prov.ttl")
    maps = rdflib.Dataset()
    for f in ("out/lv.trig", "out/ti.trig"):
        maps.parse(f, format="trig")
    mu = rdflib.Graph()
    for g in maps.graphs():
        mu += g

    shapes = rdflib.Graph()
    for f in ("inputs/usdm-rdf/usdm_v4.shapes.ttl", "inputs/usdm-rdf/usdm_v4.shapes-ct.ttl"):
        shapes.parse(f)
    ont = rdflib.Graph().parse("inputs/usdm-rdf/usdm_v4.ttl")
    conforms, rg, _ = pyshacl.validate(out, shacl_graph=shapes, ont_graph=ont, inference="none")
    results = len(list(rg.subjects(rdflib.RDF.type, rdflib.URIRef("http://www.w3.org/ns/shacl#ValidationResult"))))
    print(f"shape: conforms {conforms} | results {results}")
    assert conforms and results == 0, "SHACL"

    ct = pd.read_csv(CT_FILE, sep="\t", dtype=str, keep_default_na=False)
    members = set(zip(ct["Codelist Code"], ct["Code"], ct["CDISC Submission Value"]))
    codes = sorted(out.subjects(rdflib.RDF.type, U.Code))
    ok = 0
    for c in codes:
        rows = [x for x in prov.objects(c, JT.derivedFrom) if (x, rdflib.RDF.type, OWL.Axiom) in mu]
        assert len(rows) == 1, f"{c}: derives from {len(rows)} mapping rows"
        cl = str(mu.value(rows[0], JT.objectCodelist))
        code, decode = str(out.value(c, U["Code-code"])), str(out.value(c, U["Code-decode"]))
        version = str(out.value(c, U["Code-codeSystemVersion"]))
        if (cl, code, decode) in members and version == CT_VERSION:
            ok += 1
        else:
            print(f"  not in the package: {c} codelist {cl} code {code} decode {decode!r} version {version}")
    print(f"ct: {ok} of {len(codes)} Codes in DDF Terminology {CT_VERSION} (code, decode, codelist, version)")
    assert ok == len(codes), "CT"

    nodes = {s for s in out.subjects(rdflib.RDF.type, None)}
    no_prov = [n for n in nodes if n not in set(prov.subjects(JT.derivedFrom, None))]
    print(f"provenance: {len(nodes)} output nodes | without jt:derivedFrom {len(no_prov)}")
    assert not no_prov, "provenance"

    t = d2d_check.Transcripts(["../lzzt-layer1/transcript.trig"])
    used = set(prov.objects(None, JT.derivedFrom))
    unused = set()
    printed = 0
    for tg in t.graphs:
        for e in t.elements(tg):
            if t.printed(e):
                printed += 1
                if e not in used:
                    unused.add(str(t.u.value(e, d2d_check.D2D.localId)))
    print(f"coverage: {printed} printed elements | used {printed - len(unused)} | not used {len(unused)}: "
          + ", ".join(sorted(unused)))
    assert unused == EXPECTED_UNUSED, f"coverage: expected not used {sorted(EXPECTED_UNUSED)}"

    objs = sorted(out.subjects(rdflib.RDF.type, U.Objective))
    levels = pd.Series([str(out.value(out.value(o, U["Objective-level"]), U["Code-decode"])) for o in objs]).value_counts()
    titles = list(out.subjects(rdflib.RDF.type, U.StudyTitle))
    ns = [o for o in objs if any(str(out.value(ea, U["ExtensionAttribute-url"])) == NOT_STATED
                                 and str(out.value(ea, U["ExtensionAttribute-valueString"])) == "name"
                                 for ea in out.objects(o, U["Objective-extensionAttributes"]))]
    print(f"counts: Objectives {len(objs)} ({', '.join(f'{k} {v}' for k, v in sorted(levels.items()))}) | "
          f"StudyTitles {len(titles)} | Codes {len(codes)} | name not stated {len(ns)}")
    assert (len(objs), levels.get("Primary Objective"), levels.get("Secondary Objective"), len(titles), len(codes),
            len(ns)) == (6, 2, 4, 1, 7, 6), "counts"


if __name__ == "__main__":
    main()
