"""Our LZZT endpoints (stage 2a) next to the DDF-RA build's endpoints, per objective.

Objectives are paired by layer 1 (tests/lzzt-layer1/out/ddfra_compare.tsv: which element prints each DDF-RA objective;
ours is the Objective built from it). Within a pair, a DDF-RA endpoint and ours are paired when the instrument our row
names as printed on both protocol sides (the eo row's match_string, e.g. "CIBIC+") occurs in the DDF-RA endpoint text.
Every DDF-RA endpoint gets a row, and so does every one of ours that pairs with none.
Writes out/ddfra_endpoints_compare.tsv and compares it with expected_ddfra_endpoints.tsv; the run fails on any difference.

Usage: python3 compare_ddfra_endpoints.py   (from tests/lzzt-endpoints, after check.py and the layer-1 comparison)
"""
import json
import sys
from pathlib import Path

import pandas as pd
import rdflib

U = rdflib.Namespace("https://w3id.org/cdisc/usdm/v4/")
JT = rdflib.Namespace("urn:jt:rule-vocab:")
SSSOM = rdflib.Namespace("https://w3id.org/sssom/")
M = "urn:jt:sha256/dbadb3709bb5c41f1ede5ccf60412e9e2fa7ec18d3fdc996ec329cd80e61a040/d2d/"


def main():
    out = rdflib.Graph().parse("out/usdm.ttl")
    prov = rdflib.Graph().parse("out/prov.ttl")
    ds = rdflib.Dataset()
    ds.parse("out/eo.trig", format="trig")
    eo = rdflib.Graph()
    for g in ds.graphs():
        eo += g
    l1 = pd.read_csv("../lzzt-layer1/out/ddfra_compare.tsv", sep="\t", dtype=str, keep_default_na=False)
    d = json.loads(Path("../lzzt-layer1/inputs/downloaded/CDISC_Pilot_Study.json").read_text(encoding="utf-8"))

    def ours_objective(lid):
        e = rdflib.URIRef(M + lid)
        nodes = [s for s in prov.subjects(JT.derivedFrom, e) if (s, rdflib.RDF.type, U.Objective) in out]
        return nodes[0] if nodes else None

    def key(ep):
        rows = [x for x in prov.objects(ep, JT.derivedFrom) if (x, SSSOM.match_string, None) in eo]
        if len(rows) != 1:
            sys.exit(f"{ep}: derives from {len(rows)} endpoint-objective rows")
        return str(eo.value(rows[0], SSSOM.match_string))

    def level(ep):
        return str(out.value(out.value(ep, U["Endpoint-level"]), U["Code-decode"]))

    rows = []
    for ob in d["study"]["versions"][0]["studyDesigns"][0]["objectives"]:
        r = l1[l1["usdm_path"] == f"objectives/{ob['id']}"].iloc[0]
        o = ours_objective(r["element"]) if r["class"] in ("equal", "differs") else None
        ours = sorted(out.objects(o, U["Objective-endpoints"])) if o is not None else []
        paired = set()
        for e in ob["endpoints"]:
            hit = [x for x in ours if key(x) in e["text"]]
            if len(hit) > 1:
                sys.exit(f"{e['id']}: pairs with {len(hit)} of our endpoints")
            x = hit[0] if hit else None
            if x is not None:
                paired.add(x)
            rows.append({"ddfra_objective": ob["id"], "our_objective": r["element"], "ddfra_endpoint": e["id"],
                         "ddfra_text": " ".join(e["text"].split()), "ddfra_level": e["level"]["decode"],
                         "paired_by": key(x) if x is not None else "",
                         "our_text": str(out.value(x, U["SyntaxTemplate-text"])) if x is not None else "",
                         "our_level": level(x) if x is not None else ""})
        for x in ours:
            if x not in paired:
                rows.append({"ddfra_objective": ob["id"], "our_objective": r["element"], "ddfra_endpoint": "",
                             "ddfra_text": "", "ddfra_level": "", "paired_by": "",
                             "our_text": str(out.value(x, U["SyntaxTemplate-text"])), "our_level": level(x)})
    df = pd.DataFrame(rows)
    Path("out").mkdir(exist_ok=True)
    df.to_csv("out/ddfra_endpoints_compare.tsv", sep="\t", index=False)
    both = df[(df["ddfra_endpoint"] != "") & (df["our_text"] != "")]
    print(f"endpoints: DDF-RA {int((df['ddfra_endpoint'] != '').sum())} | ours {int((df['our_text'] != '').sum())} | "
          f"paired {len(both)} (same level {int((both['ddfra_level'] == both['our_level']).sum())}) | "
          f"DDF-RA only {int(((df['ddfra_endpoint'] != '') & (df['our_text'] == '')).sum())} | "
          f"ours only {int(((df['ddfra_endpoint'] == '') & (df['our_text'] != '')).sum())}")
    exp = pd.read_csv("expected_ddfra_endpoints.tsv", sep="\t", dtype=str, keep_default_na=False)
    got = pd.read_csv("out/ddfra_endpoints_compare.tsv", sep="\t", dtype=str, keep_default_na=False)
    same = exp.equals(got)
    print(f"expected: {len(exp)} rows | this run: {len(got)} rows | identical: {'yes' if same else 'NO'}")
    if not same:
        sys.exit("out/ddfra_endpoints_compare.tsv differs from expected_ddfra_endpoints.tsv")


if __name__ == "__main__":
    main()
