"""Compare the DDF-RA USDM build of the CDISC Pilot (LZZT) with the d2d transcript of the printed pages.

For each in-scope DDF-RA value (titles, study identifiers, objectives, endpoints), say how it relates to what the
transcribed pages print, under the transcript run's normalization (whitespace collapsed; nothing else):
  equal        the value is the printed text of one transcript element
  contained    the value is printed inside one transcript element's text (e.g. an identifier in a longer line)
  differs      no element prints it, but one element's text is close (difflib ratio >= 0.8); both are shown
  not printed  none of the above on the transcribed pages
  placeholder  the value is a builder's placeholder, printed as "*** ... ***"
The result is written to out/ddfra_compare.tsv and compared with expected_ddfra.tsv; the run fails on any
difference. Findings are recorded, not resolved: the build is not ours.

Usage: python3 compare_ddfra.py   (from tests/lzzt-layer1)
"""
import difflib
import json
import re
import sys
from pathlib import Path

import pandas as pd
import rdflib

D2D = rdflib.Namespace("urn:jt:d2d:")
RATIO = 0.8


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def main():
    ds = rdflib.Dataset()
    ds.parse("transcript.trig", format="trig")
    els = {}
    for g in ds.graphs():
        for e, lid in g.subject_objects(D2D.localId):
            t = g.value(e, D2D.text)
            if t is not None:
                els[str(lid)] = str(t)
    if not els:
        sys.exit("transcript.trig: no element with d2d:text")

    d = json.loads(Path("inputs/downloaded/CDISC_Pilot_Study.json").read_text(encoding="utf-8"))
    sv = d["study"]["versions"][0]
    sd = sv["studyDesigns"]
    if len(sd) != 1:
        sys.exit(f"expected one study design, found {len(sd)}")
    values = [(f"titles/{t['type']['decode']}", t["text"]) for t in sv["titles"]]
    values += [(f"studyIdentifiers/{i['scopeId']}", i["text"]) for i in sv["studyIdentifiers"]]
    for o in sd[0]["objectives"]:
        values.append((f"objectives/{o['id']}", o["text"]))
        values += [(f"objectives/{o['id']}/endpoints/{e['id']}", e["text"]) for e in o["endpoints"]]

    rows = []
    for path, raw in values:
        v = norm(raw)
        equal = [k for k, t in els.items() if t == v]
        inside = [k for k, t in els.items() if v in t and t != v]
        if v.startswith("***") and v.endswith("***"):
            cls, el = "placeholder", ""
        elif len(equal) == 1:
            cls, el = "equal", equal[0]
        elif equal:
            sys.exit(f"{path}: printed by more than one element: {equal}")
        elif inside:
            cls, el = "contained", ";".join(sorted(inside))
        else:
            best = max(els, key=lambda k: difflib.SequenceMatcher(None, v, els[k]).ratio())
            r = difflib.SequenceMatcher(None, v, els[best]).ratio()
            cls, el = ("differs", best) if r >= RATIO else ("not printed", "")
        rows.append({"usdm_path": path, "usdm_text": v, "class": cls, "element": el,
                     "element_text": els[el] if cls in ("equal", "differs") else ""})
    df = pd.DataFrame(rows)
    Path("out").mkdir(exist_ok=True)
    df.to_csv("out/ddfra_compare.tsv", sep="\t", index=False)
    counts = df["class"].value_counts()
    print("DDF-RA values: " + str(len(df)) + " | " + " | ".join(f"{k}: {counts.get(k, 0)}" for k in
          ("equal", "contained", "differs", "not printed", "placeholder")))
    exp = pd.read_csv("expected_ddfra.tsv", sep="\t", dtype=str, keep_default_na=False)
    got = pd.read_csv("out/ddfra_compare.tsv", sep="\t", dtype=str, keep_default_na=False)
    same = exp.equals(got)
    print(f"expected: {len(exp)} rows | this run: {len(got)} rows | identical: {'yes' if same else 'NO'}")
    if not same:
        sys.exit("out/ddfra_compare.tsv differs from expected_ddfra.tsv")


if __name__ == "__main__":
    main()
