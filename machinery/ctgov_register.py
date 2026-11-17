"""ctgov_register — the register of Studies, Works, Expressions and Manifestations, from a hand-kept assignments
table and pinned ClinicalTrials.gov records (API v2 JSON, one file per NCT id).

The table holds the decisions: which opaque ids (s/w/e + four digits) a study, its protocol and a protocol version get,
which file of record embodies the version, and who reviewed that. Every other fact comes from the pinned record: the
study's registered identifiers and brief title, the large document's label, date and size. Nothing is read from the
document itself.

CTGOV_DIR holds the records and SOURCES.tsv (file, url, retrieved_on): where and when each record was retrieved.

Usage: python3 ctgov_register.py ASSIGNMENTS.tsv CTGOV_DIR OUT.trig [--base urn:jt:]
Writes one named graph {B}register.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import rdflib

sys.path.insert(0, str(Path(__file__).parent))
import d2d_iri as I  # noqa: E402

COLUMNS = ["study_id", "nct_id", "work_id", "expression_id", "ctgov_document", "manifestation_sha256",
           "manifestation_url", "retrieved_on", "author_label", "reviewer_id", "comment"]


def q(s):
    return rdflib.Literal(s).n3()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("assignments")
    ap.add_argument("ctgov_dir")
    ap.add_argument("out")
    ap.add_argument("--base", default=I.BASE)
    a = ap.parse_args()
    B = a.base
    df = pd.read_csv(a.assignments, sep="\t", dtype=str, keep_default_na=False)
    if list(df.columns) != COLUMNS:
        sys.exit(f"{a.assignments}: columns must be {COLUMNS}")
    for col in COLUMNS[:-1]:
        if (df[col] == "").any():
            sys.exit(f"{a.assignments}: empty {col}")
    if df["expression_id"].duplicated().any():
        sys.exit(f"{a.assignments}: expression_id must be unique: one Manifestation per Expression is transcribed")
    for key, val in (("nct_id", "study_id"), ("expression_id", "work_id"), ("work_id", "study_id")):
        if (df.groupby(key)[val].nunique() > 1).any():
            sys.exit(f"{a.assignments}: one {key} with more than one {val}")

    src = pd.read_csv(Path(a.ctgov_dir) / "SOURCES.tsv", sep="\t", dtype=str, keep_default_na=False)
    if list(src.columns) != ["file", "url", "retrieved_on"] or src["file"].duplicated().any():
        sys.exit(f"{a.ctgov_dir}/SOURCES.tsv: columns must be file, url, retrieved_on; one row per file")
    src = src.set_index("file")
    used = {}
    studies, works, lines = {}, {}, []
    for _, r in df.iterrows():
        rec_path = Path(a.ctgov_dir) / f"{r['nct_id']}.json"
        used[rec_path] = I.sha256_file(rec_path)
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        idm = rec["protocolSection"]["identificationModule"]
        if idm["nctId"] != r["nct_id"]:
            sys.exit(f"{rec_path}: nctId {idm['nctId']} is not {r['nct_id']}")
        docs = [d for d in rec["documentSection"]["largeDocumentModule"]["largeDocs"]
                if d["filename"] == r["ctgov_document"]]
        if len(docs) != 1:
            sys.exit(f"{rec_path}: no single large document named {r['ctgov_document']}")
        doc = docs[0]
        s = I.study_iri(I.register_number(r["study_id"], "s"), B)
        w = I.work_iri(I.register_number(r["work_id"], "w"), B)
        e = I.expression_iri(I.register_number(r["expression_id"], "e"), B)
        m = I.file_iri(r["manifestation_sha256"], B)
        if s not in studies:
            ids = [("nctId", idm["nctId"], None, None),
                   ("orgStudyIdInfo", idm["orgStudyIdInfo"]["id"], idm["orgStudyIdInfo"].get("type"), None)]
            ids += [("secondaryIdInfos", x["id"], x.get("type"), x.get("domain"))
                    for x in idm.get("secondaryIdInfos", [])]
            nodes = []
            for field, value, typ, dom in ids:
                n = f"[ d2d:idField {q(field)} ; d2d:idValue {q(value)}"
                n += f" ; d2d:idType {q(typ)}" if typ else ""
                n += f" ; d2d:idDomain {q(dom)}" if dom else ""
                nodes.append(n + " ]")
            studies[s] = (f"<{s}> a obo:OBI_0000066 ;\n    rdfs:label {q(idm['briefTitle'])} ;\n"
                          f"    prov:wasDerivedFrom <{I.file_iri(used[rec_path], B)}> ;\n"
                          "    d2d:registeredId " + " ,\n        ".join(nodes) + " .")
        if w not in works:
            works[w] = (f"<{w}> a frbr:Work ;\n    obo:IAO_0000136 <{s}> ;\n"
                        f"    prov:wasAttributedTo <{r['reviewer_id']}> .")
        lines.append(f"<{e}> a frbr:Expression ;\n    frbr:realizationOf <{w}> ;\n"
                     f"    dcterms:type {q(doc['label'])} ;\n    dcterms:date \"{doc['date']}\"^^xsd:date ;\n"
                     f"    prov:wasDerivedFrom <{I.file_iri(used[rec_path], B)}> ;\n"
                     f"    prov:wasAttributedTo <{r['reviewer_id']}> .")
        lines.append(f"<{m}> a frbr:Manifestation ;\n    frbr:embodimentOf <{e}> ;\n"
                     f"    d2d:sha256 {q(r['manifestation_sha256'])} ;\n    d2d:byteSize {int(doc['size'])} ;\n"
                     f"    pav:retrievedFrom <{r['manifestation_url']}> ;\n"
                     f"    pav:retrievedOn \"{r['retrieved_on']}\"^^xsd:dateTime ;\n"
                     f"    rdfs:comment {q(r['comment'])} ;\n"
                     f"    prov:wasAttributedTo <{r['reviewer_id']}> .")
    tsv = I.file_iri(I.sha256_file(a.assignments), B)
    stsv = I.file_iri(I.sha256_file(Path(a.ctgov_dir) / "SOURCES.tsv"), B)
    head = [f"<{B}register> a prov:Entity ;\n"
            "    prov:wasDerivedFrom " + " , ".join(f"<{I.file_iri(h, B)}>" for h in sorted(set(used.values())))
            + f" , <{tsv}> , <{stsv}> ."]
    for p, h in sorted(used.items()):
        if p.name not in src.index:
            sys.exit(f"{a.ctgov_dir}/SOURCES.tsv: no row for {p.name}")
        label = q("ClinicalTrials.gov API v2 record " + p.name)
        head.append(f"<{I.file_iri(h, B)}> a prov:Entity ; rdfs:label {label} ;\n"
                    f"    pav:retrievedFrom <{src.loc[p.name, 'url']}> ;\n"
                    f"    pav:retrievedOn \"{src.loc[p.name, 'retrieved_on']}\"^^xsd:dateTime .")
    head.append(f"<{tsv}> a prov:Entity ; rdfs:label {q(Path(a.assignments).name)} .")
    head.append(f"<{stsv}> a prov:Entity ; rdfs:label \"SOURCES.tsv\" .")
    prefixes = """@prefix d2d:     <urn:jt:d2d:> .
@prefix obo:     <http://purl.obolibrary.org/obo/> .
@prefix frbr:    <http://purl.org/vocab/frbr/core#> .
@prefix prov:    <http://www.w3.org/ns/prov#> .
@prefix pav:     <http://purl.org/pav/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
"""
    body = "\n\n".join(head + [studies[k] for k in sorted(studies)] + [works[k] for k in sorted(works)] + lines)
    text = (f"# Register, generated by ctgov_register.py from {Path(a.assignments).name} and pinned ClinicalTrials.gov "
            f"records. Do not edit; edit the assignments table.\n" + prefixes + f"\n<{B}register> {{\n{body}\n}}\n")
    Path(a.out).write_text(text, encoding="utf-8")
    g = rdflib.Dataset()
    g.parse(a.out, format="trig")
    print(f"register: {len(df)} expression(s), {len(studies)} study(ies), {len(works)} work(s) -> {a.out} "
          f"({len(g)} quads)")


if __name__ == "__main__":
    main()
