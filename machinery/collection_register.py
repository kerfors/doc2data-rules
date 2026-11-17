"""collection_register — register entries for protocols that come from a soa2usdm collection, not from
ClinicalTrials.gov: Studies, Works, Expressions and Manifestations, from a hand-kept assignments table and the pinned
collection workbook (studies_protocols.xlsx, sheets "studies" and "protocols").

The table holds the decisions: which opaque ids (s/w/e + four digits) a study, its protocol and a protocol version get,
which file of record embodies the version (its sha256 and size as downloaded), and who reviewed that. The study's
identifiers and the protocol URL come from the pinned workbook; the URL in the table must equal the workbook's
protocol_url. Nothing is read from the document itself.

COLLECTIONS_DIR holds one folder per collection with its workbook, and SOURCES.tsv (file, url, retrieved_on): where and
when each workbook was retrieved.

Usage: python3 collection_register.py ASSIGNMENTS.tsv COLLECTIONS_DIR OUT.trig [--base urn:jt:]
Writes one named graph {B}register/collections.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd
import rdflib

sys.path.insert(0, str(Path(__file__).parent))
import d2d_iri as I  # noqa: E402

COLUMNS = ["study_id", "collection", "collection_key", "work_id", "expression_id", "manifestation_sha256",
           "manifestation_byte_size", "manifestation_url", "retrieved_on", "author_label", "reviewer_id", "comment"]
ID_FIELDS = ["nct_id", "study_code", "study_acronym"]


def q(s):
    return rdflib.Literal(s).n3()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("assignments")
    ap.add_argument("collections_dir")
    ap.add_argument("out")
    ap.add_argument("--base", default=I.BASE)
    a = ap.parse_args()
    B = a.base
    G = f"{B}register/collections"
    df = pd.read_csv(a.assignments, sep="\t", dtype=str, keep_default_na=False)
    if list(df.columns) != COLUMNS:
        sys.exit(f"{a.assignments}: columns must be {COLUMNS}")
    for col in COLUMNS[:-1]:
        if (df[col] == "").any():
            sys.exit(f"{a.assignments}: empty {col}")
    if df["expression_id"].duplicated().any():
        sys.exit(f"{a.assignments}: expression_id must be unique: one Manifestation per Expression is transcribed")
    for key, val in (("collection_key", "study_id"), ("expression_id", "work_id"), ("work_id", "study_id")):
        if (df.groupby(key)[val].nunique() > 1).any():
            sys.exit(f"{a.assignments}: one {key} with more than one {val}")

    src = pd.read_csv(Path(a.collections_dir) / "SOURCES.tsv", sep="\t", dtype=str, keep_default_na=False)
    if list(src.columns) != ["file", "url", "retrieved_on"] or src["file"].duplicated().any():
        sys.exit(f"{a.collections_dir}/SOURCES.tsv: columns must be file, url, retrieved_on; one row per file")
    src = src.set_index("file")
    used = {}
    studies, works, lines = {}, {}, []
    for _, r in df.iterrows():
        rel = f"{r['collection']}/studies_protocols.xlsx"
        wb_path = Path(a.collections_dir) / rel
        used[rel] = I.sha256_file(wb_path)
        wb = I.file_iri(used[rel], B)
        st = pd.read_excel(wb_path, sheet_name="studies", dtype=str).fillna("")
        pr = pd.read_excel(wb_path, sheet_name="protocols", dtype=str).fillna("")
        srow = st[st["d4k_folder"] == r["collection_key"]]
        if len(srow) != 1:
            sys.exit(f"{wb_path}: sheet studies has {len(srow)} rows with d4k_folder {r['collection_key']}, needs 1")
        srow = srow.iloc[0]
        # the protocols sheet keys its rows in column nct_id, which holds the d4k folder when there is no NCT id
        key = srow["nct_id"] if srow["nct_id"] else r["collection_key"]
        prow = pr[pr["nct_id"] == key]
        if len(prow) != 1:
            sys.exit(f"{wb_path}: sheet protocols has {len(prow)} rows with nct_id {key}, needs 1")
        if prow.iloc[0]["protocol_url"] != r["manifestation_url"]:
            sys.exit(f"{a.assignments}: manifestation_url {r['manifestation_url']} is not the workbook's protocol_url "
                     f"{prow.iloc[0]['protocol_url']}")
        s = I.study_iri(I.register_number(r["study_id"], "s"), B)
        w = I.work_iri(I.register_number(r["work_id"], "w"), B)
        e = I.expression_iri(I.register_number(r["expression_id"], "e"), B)
        m = I.file_iri(r["manifestation_sha256"], B)
        if s not in studies:
            ids = [(f, srow[f]) for f in ID_FIELDS if srow[f]]
            if not ids:
                sys.exit(f"{wb_path}: no identifier for {r['collection_key']} in {ID_FIELDS}")
            nodes = [f"[ d2d:idField {q(f)} ; d2d:idValue {q(v)} ]" for f, v in ids]
            studies[s] = (f"<{s}> a obo:OBI_0000066 ;\n    rdfs:label {q(srow['study_acronym'] or r['collection_key'])} ;\n"
                          f"    prov:wasDerivedFrom <{wb}> ;\n"
                          "    d2d:registeredId " + " ,\n        ".join(nodes) + " .")
        if w not in works:
            works[w] = (f"<{w}> a frbr:Work ;\n    obo:IAO_0000136 <{s}> ;\n"
                        f"    prov:wasAttributedTo <{r['reviewer_id']}> .")
        lines.append(f"<{e}> a frbr:Expression ;\n    frbr:realizationOf <{w}> ;\n"
                     f"    prov:wasDerivedFrom <{wb}> ;\n"
                     f"    prov:wasAttributedTo <{r['reviewer_id']}> .")
        lines.append(f"<{m}> a frbr:Manifestation ;\n    frbr:embodimentOf <{e}> ;\n"
                     f"    d2d:sha256 {q(r['manifestation_sha256'])} ;\n"
                     f"    d2d:byteSize {int(r['manifestation_byte_size'])} ;\n"
                     f"    pav:retrievedFrom <{r['manifestation_url']}> ;\n"
                     f"    pav:retrievedOn \"{r['retrieved_on']}\"^^xsd:dateTime ;\n"
                     f"    rdfs:comment {q(r['comment'])} ;\n"
                     f"    prov:wasAttributedTo <{r['reviewer_id']}> .")
    tsv = I.file_iri(I.sha256_file(a.assignments), B)
    stsv = I.file_iri(I.sha256_file(Path(a.collections_dir) / "SOURCES.tsv"), B)
    head = [f"<{G}> a prov:Entity ;\n"
            "    prov:wasDerivedFrom " + " , ".join(f"<{I.file_iri(h, B)}>" for h in sorted(set(used.values())))
            + f" , <{tsv}> , <{stsv}> ."]
    for rel, h in sorted(used.items()):
        if rel not in src.index:
            sys.exit(f"{a.collections_dir}/SOURCES.tsv: no row for {rel}")
        label = q("soa2usdm collection workbook " + rel)
        head.append(f"<{I.file_iri(h, B)}> a prov:Entity ; rdfs:label {label} ;\n"
                    f"    pav:retrievedFrom <{src.loc[rel, 'url']}> ;\n"
                    f"    pav:retrievedOn \"{src.loc[rel, 'retrieved_on']}\"^^xsd:dateTime .")
    head.append(f"<{tsv}> a prov:Entity ; rdfs:label {q(Path(a.assignments).name)} .")
    head.append(f"<{stsv}> a prov:Entity ; rdfs:label \"SOURCES.tsv\" .")
    prefixes = """@prefix d2d:     <urn:jt:d2d:> .
@prefix obo:     <http://purl.obolibrary.org/obo/> .
@prefix frbr:    <http://purl.org/vocab/frbr/core#> .
@prefix prov:    <http://www.w3.org/ns/prov#> .
@prefix pav:     <http://purl.org/pav/> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
"""
    body = "\n\n".join(head + [studies[k] for k in sorted(studies)] + [works[k] for k in sorted(works)] + lines)
    text = (f"# Register (collections), generated by collection_register.py from {Path(a.assignments).name} and "
            f"pinned soa2usdm collection workbooks. Do not edit; edit the assignments table.\n" + prefixes
            + f"\n<{G}> {{\n{body}\n}}\n")
    Path(a.out).write_text(text, encoding="utf-8")
    g = rdflib.Dataset()
    g.parse(a.out, format="trig")
    print(f"register (collections): {len(df)} expression(s), {len(studies)} study(ies), {len(works)} work(s) -> "
          f"{a.out} ({len(g)} quads)")


if __name__ == "__main__":
    main()
