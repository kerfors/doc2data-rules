"""Check the Q7 rule runs against the Python build, then derive the affected-statements list by comparing runs.

Part A  inheritance readings: run core41 against inheritance_readings.csv (script 07), row by row. The
        target_change column is not produced by any rule: it is read off the two runs (the section
        expression each target resolved to in run core40 and in run core41, by text).
Part B  affected statements: a reading is affected when the section texts it derives from (provenance
        graph) differ between run core40 and run core41. Compared with statement_versions.csv (script 08),
        row by row, without its display column first_change_in_4_1 (taken from another pipeline's diff).
Run from this folder after both runs.
"""
import hashlib
from collections import Counter

import pandas as pd
import rdflib
from rdflib import Namespace, RDF, URIRef

ECDR = "inputs/ecdr-8c374cc/remapcap-design-modules"
F = Namespace("urn:q7:fact-vocab:")
RC = Namespace("urn:q7:vocab:")
M = Namespace("urn:q7:map-vocab:")
DERIVED = URIRef("urn:jt:rule-vocab:derivedFrom")

facts = rdflib.Graph()
for f in ["facts.trig", "facts_core41.trig"]:
    ds = rdflib.Dataset()
    ds.parse(f, format="trig")
    for g in ds.graphs():
        facts += g
mapping = rdflib.Dataset()
mapping.parse("mapping.trig", format="trig")
mapping = mapping.graph(URIRef("urn:jt:g:topic-rules"))
runs = {k: rdflib.Graph().parse(f"out/{k}/q7_readings.ttl") for k in ["core40", "core41"]}
prov = {k: rdflib.Graph().parse(f"out/{k}/prov.ttl") for k in ["core40", "core41"]}


def s(g, node, p):
    v = g.value(node, p)
    return "" if v is None else str(v)


def label(out, w):
    return f"{s(out, w, RC.layer)} {s(out, w, RC.number)}"


def doc_key(expr):
    return s(facts, facts.value(expr, F.doc), F.key)


# Gate on the mapping data (as script 07 asserts): a topic rule's title term is in each target's Core 4.1 / PANDA title
title41 = {}
for e in facts.subjects(RDF.type, F.Section):
    if doc_key(e) in ("CORE41", "PANDA"):
        layer = "CORE" if doc_key(e) == "CORE41" else "PANDA"
        title41[f"{layer} {s(facts, e, F.number)}"] = s(facts, e, F.title)
for t in mapping.subjects(RDF.type, M.TopicRule):
    term = s(mapping, t, M.titleTerm)
    for w in mapping.objects(t, M.target):
        key = str(w).split(":")[-1].replace("/", " ")
        assert key in title41, f"topic rule {s(mapping, t, M.order)}: no section {key}"
        assert term.lower() in title41[key].lower(), f"topic rule {s(mapping, t, M.order)}: {term!r} not in {title41[key]!r}"
print("gate ok: topic-rule targets exist and title terms are in the target titles")


def expr_by_target(run):
    out = runs[run]
    res = {}
    for r, e in out.subject_objects(RC.resolvesToExpression):
        res[(r, out.value(e, RC.expressionOf))] = e
    return res


e40, e41 = expr_by_target("core40"), expr_by_target("core41")


def change(r, w):
    if (r, w) not in e41:
        return ""
    if (r, w) not in e40:
        return "new in 4.1"
    t40, t41 = s(facts, e40[(r, w)], F.text), s(facts, e41[(r, w)], F.text)
    return "changed in 4.1" if t40 != t41 else ""


# ---------------- Part A ----------------
out = runs["core41"]
rows = []
for r in out.subjects(RDF.type, RC.Reading):
    st = out.value(r, RC.statement)
    ws = list(out.objects(r, RC.resolvesTo))
    rows.append({
        "doc": s(facts, facts.value(st, F.doc), F.key), "section": s(facts, st, F.section),
        "relation": s(facts, st, F.relation), "target_phrase": s(out, r, RC.targetPhrase),
        "binding": s(out, r, RC.binding),
        "resolution": ";".join(sorted(label(out, w) for w in ws)),
        "rule": s(out, r, RC.rule), "rule_source": s(out, r, RC.ruleSource),
        "all_matching_rules": ";".join(str(o) for o in sorted(int(o) for o in out.objects(r, RC.matchingRule))),
        "target_titles": " | ".join(sorted(s(facts, e41[(r, w)], F.title) for w in ws if (r, w) in e41)),
        "target_change": ";".join(sorted(c for c in (change(r, w) for w in ws) if c)),
        "status": "analyst-reading", "sentence": s(facts, st, F.sentence), "_reading": r})
mine = pd.DataFrame(rows)
assert len(mine) == len(mine.drop_duplicates(["doc", "section", "sentence"])), "two readings for one statement"

py = pd.read_csv(f"{ECDR}/output/step5/inheritance_readings.csv", dtype=str, keep_default_na=False)
py["resolution"] = py.resolution.map(lambda v: ";".join(sorted(v.split(";"))) if v else "")
py["target_titles"] = py.target_titles.map(lambda v: " | ".join(sorted(v.split(" | "))) if v else "")
py["target_change"] = py.target_change.map(lambda v: ";".join(sorted(v.split(";"))) if v else "")
cols = [c for c in py.columns]
key = ["doc", "section", "sentence"]
both = py.merge(mine[cols], on=key, how="outer", suffixes=("_py", "_rules"), indicator=True)
print(f"\nPart A, inheritance readings: Python {len(py)} | rules {len(mine)} | "
      f"only Python {int((both._merge == 'left_only').sum())} | only rules {int((both._merge == 'right_only').sum())}")
diff_cols = {}
for c in cols:
    if c in key:
        continue
    d = both[(both._merge == "both") & (both[c + "_py"] != both[c + "_rules"])]
    diff_cols[c] = len(d)
    for x in d.itertuples():
        print(f"   {c}: {x.doc} {x.section}: Python {getattr(x, c + '_py')!r} | rules {getattr(x, c + '_rules')!r}")
identical = int((both._merge == "both").sum()) - len(
    set().union(*[set(both[(both._merge == "both") & (both[c + "_py"] != both[c + "_rules"])].index)
                  for c in cols if c not in key]))
print(f"   identical on all {len(cols)} columns: {identical} (resolution, target_titles, target_change compared as sorted sets)")
print("   resolved:", int((mine.resolution != "").sum()), "| by rule_source:",
      dict(Counter(v if not v.startswith(("agreed", "title", "nine")) else "topic rule" for v in mine.rule_source)))

# ---------------- Part B ----------------
def inputs(run, r):
    """Section texts a reading derives from, by provenance (sha256 of each text)."""
    return frozenset(hashlib.sha256(s(facts, e, F.text).encode()).hexdigest()
                     for e in prov[run].objects(r, DERIVED) if (e, RDF.type, F.Section) in facts)


affected = [r for r in mine._reading if inputs("core40", r) != inputs("core41", r)]
print(f"\nPart B, affected statements (section inputs differ between run core40 and run core41): {len(affected)}")
changed_readings = set(mine[mine.target_change != ""]._reading)
print(f"   same set as readings with a target_change: {set(affected) == changed_readings}")

core41 = URIRef("urn:q7:fact:doc/CORE41")
d41 = facts.value(core41, F.date).toPython()
by_reading = {row["_reading"]: row for row in rows}
srows = []
for r in affected:
    a = pd.Series(by_reading[r])
    st = out.value(r, RC.statement)
    ddate = facts.value(facts.value(st, F.doc), F.date).toPython()
    vers = sorted({s(facts, facts.value(e, F.doc), F.version) for e in out.objects(r, RC.resolvesToExpression)})
    add = sorted({s(facts, facts.value(e, F.doc), F.version) for e in out.objects(r, RC.additionallyResolvesToExpression)})
    srows.append({"doc": a.doc, "doc_date": ddate.isoformat(), "dated_before_core_4_1": str(ddate < d41),
                  "section": a.section, "target_phrase": a.target_phrase, "resolution": a.resolution,
                  "resolves_to_core_versions": " + ".join(vers) + "".join(f" + {v} (additionally)" for v in add),
                  "rule": "V-current + V-transition" if add else "V-current",
                  "status": "analyst-reading", "sentence": a.sentence})
sv_mine = pd.DataFrame(srows)
sv = pd.read_csv(f"{ECDR}/output/step5/statement_versions.csv", dtype=str, keep_default_na=False)
sv = sv.drop(columns=["first_change_in_4_1"])
sv["resolution"] = sv.resolution.map(lambda v: ";".join(sorted(v.split(";"))))
tup = lambda df: set(map(tuple, df[sv.columns].values.tolist()))
print(f"   statement_versions: Python {len(sv)} | rules {len(sv_mine)} | identical {len(tup(sv) & tup(sv_mine))} "
      f"(all columns except first_change_in_4_1)")
for x in sorted(tup(sv) - tup(sv_mine)):
    print("   only in Python:", x[:7])
for x in sorted(tup(sv_mine) - tup(sv)):
    print("   only in rules: ", x[:7])
t = sv_mine.groupby(["doc", "doc_date"]).resolves_to_core_versions.value_counts().unstack(fill_value=0)
t.insert(0, "R6s", t.sum(axis=1))
print("\nR6s / R7 per DSA (rules):")
print(t.to_string())

assert (both._merge == "both").all() and identical == len(py), f"Part A differs: identical {identical} of Python {len(py)} | rules {len(mine)}"
assert set(affected) == changed_readings, "Part B: affected statements are not the readings with a target_change"
assert len(sv) == len(sv_mine) and tup(sv) == tup(sv_mine), f"Part B: statement_versions differ: Python {len(sv)} | rules {len(sv_mine)} | identical {len(tup(sv) & tup(sv_mine))}"
