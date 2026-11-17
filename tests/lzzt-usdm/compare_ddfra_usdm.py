"""Our LZZT stage-1 USDM build next to the DDF-RA build of the same study, value by value.

Pairs come from layer 1, not from order or similarity here: tests/lzzt-layer1/out/ddfra_compare.tsv says which transcript
element prints each DDF-RA objective or title (equal or differs); our node is the one built from that element (out/prov.ttl).
For each pair and attribute: the DDF-RA value, ours, and whether they are the same. For Codes, also whether code + decode
are in each pinned DDF CT package (2024-09-27, the version DDF-RA states; 2026-09-25, the version we use), under the
codelist USDM binds the attribute to. DDF-RA values with no pair are listed with what layer 1 found.
Writes out/ddfra_usdm_compare.tsv and compares it with expected_ddfra_usdm.tsv; the run fails on any difference.

Usage: python3 compare_ddfra_usdm.py   (from tests/lzzt-usdm, after check.py and the layer-1 comparison)
"""
import json
import sys
from pathlib import Path

import pandas as pd
import rdflib

U = rdflib.Namespace("https://w3id.org/cdisc/usdm/v4/")
JT = rdflib.Namespace("urn:jt:rule-vocab:")
M = "urn:jt:sha256/dbadb3709bb5c41f1ede5ccf60412e9e2fa7ec18d3fdc996ec329cd80e61a040/d2d/"
NOT_STATED = "https://kerfors.github.io/soa2usdm/not-stated-in-protocol"
PACKAGES = {"2024-09-27": "inputs/downloaded/DDF_Terminology_2024-09-27.txt",
            "2026-09-25": "inputs/downloaded/DDF_Terminology_2026-09-25.txt"}
CODELIST = {"objectives": "C188725", "titles": "C207419"}


def main():
    out = rdflib.Graph().parse("out/usdm.ttl")
    prov = rdflib.Graph().parse("out/prov.ttl")
    l1 = pd.read_csv("../lzzt-layer1/out/ddfra_compare.tsv", sep="\t", dtype=str, keep_default_na=False)
    d = json.loads(Path("../lzzt-layer1/inputs/downloaded/CDISC_Pilot_Study.json").read_text(encoding="utf-8"))
    sv = d["study"]["versions"][0]
    pk = {}
    for v, f in PACKAGES.items():
        ct = pd.read_csv(f, sep="\t", dtype=str, keep_default_na=False)
        pk[v] = set(zip(ct["Codelist Code"], ct["Code"], ct["CDISC Submission Value"]))

    def ours_from(lid, cls):
        e = rdflib.URIRef(M + lid)
        nodes = [s for s in prov.subjects(JT.derivedFrom, e) if (s, rdflib.RDF.type, cls) in out]
        if len(nodes) > 1:
            sys.exit(f"{lid}: more than one {cls} built from it")
        return nodes[0] if nodes else None

    def in_pk(cl, code, decode):
        return {v: ("yes" if (cl, code, decode) in s else "no") for v, s in pk.items()}

    rows = []

    def add(path, attr, theirs, ours, compare=True):
        rows.append({"ddfra_path": path, "attribute": attr, "ddfra": theirs, "ours": ours,
                     "same": ("yes" if theirs == ours else "no") if compare else ""})

    def code_rows(path, cl, tc, oc):
        o = {} if oc is None else {"code": str(out.value(oc, U["Code-code"])),
                                   "decode": str(out.value(oc, U["Code-decode"])),
                                   "version": str(out.value(oc, U["Code-codeSystemVersion"]))}
        add(path, "code", tc["code"], o.get("code", ""))
        add(path, "decode", tc["decode"], o.get("decode", ""))
        add(path, "codeSystemVersion", tc["codeSystemVersion"], o.get("version", ""))
        t_in = in_pk(cl, tc["code"], tc["decode"])
        o_in = in_pk(cl, o["code"], o["decode"]) if o else {v: "" for v in pk}
        for v in pk:
            add(path, f"code+decode in DDF CT {v}", t_in[v], o_in[v])

    for ob in sv["studyDesigns"][0]["objectives"]:
        path = f"objectives/{ob['id']}"
        r = l1[l1["usdm_path"] == path].iloc[0]
        node = ours_from(r["element"], U.Objective) if r["class"] in ("equal", "differs") else None
        add(path, "paired by layer 1", r["class"], r["element"], compare=False)
        add(path, "text", " ".join(ob["text"].split()), "" if node is None else str(out.value(node, U["SyntaxTemplate-text"])))
        name = "" if node is None else str(out.value(node, U["SyntaxTemplate-name"]))
        ns = node is not None and any(str(out.value(ea, U["ExtensionAttribute-url"])) == NOT_STATED
                                      for ea in out.objects(node, U["Objective-extensionAttributes"]))
        add(path, "name", ob["name"], f"{name!r} + not stated" if ns else name)
        code_rows(path + "/level", CODELIST["objectives"], ob["level"],
                  None if node is None else out.value(node, U["Objective-level"]))
        add(path, "endpoints", str(len(ob["endpoints"])),
            "" if node is None else str(len(list(out.objects(node, U["Objective-endpoints"])))))
    for ti in sv["titles"]:
        path = f"titles/{ti['type']['decode']}"
        r = l1[l1["usdm_path"] == path].iloc[0]
        node = ours_from(r["element"], U.StudyTitle) if r["class"] in ("equal", "differs") else None
        add(path, "paired by layer 1", r["class"], r["element"], compare=False)
        add(path, "text", " ".join(ti["text"].split()), "" if node is None else str(out.value(node, U["StudyTitle-text"])))
        code_rows(path + "/type", CODELIST["titles"], ti["type"],
                  None if node is None else out.value(node, U["StudyTitle-type"]))

    df = pd.DataFrame(rows)
    Path("out").mkdir(exist_ok=True)
    df.to_csv("out/ddfra_usdm_compare.tsv", sep="\t", index=False)
    print(f"DDF-RA vs ours: {len(df)} rows | same {int((df['same'] == 'yes').sum())} | differ {int((df['same'] == 'no').sum())} "
          f"| pairing rows {int((df['same'] == '').sum())}")
    exp = pd.read_csv("expected_ddfra_usdm.tsv", sep="\t", dtype=str, keep_default_na=False)
    got = pd.read_csv("out/ddfra_usdm_compare.tsv", sep="\t", dtype=str, keep_default_na=False)
    same = exp.equals(got)
    print(f"expected: {len(exp)} rows | this run: {len(got)} rows | identical: {'yes' if same else 'NO'}")
    if not same:
        sys.exit("out/ddfra_usdm_compare.tsv differs from expected_ddfra_usdm.tsv")


if __name__ == "__main__":
    main()
