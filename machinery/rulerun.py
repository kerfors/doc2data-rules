"""rulerun — compile L/R rules (jt: vocabulary) to SPARQL Update and run them over facts.

A rule is two named graphs in TriG: a match graph (L) and a construct graph (R), plus optional negative
graphs (each a FILTER NOT EXISTS), filters, computed values and minted IRIs. Rules run in jt:seq order
against an in-memory Oxigraph store. Each rule writes into its own firing graph; jt:derivedFrom triples go
to a separate provenance graph, never into the output; each run is recorded in a firings graph.

Vocabulary (see ../VOCABULARY.md):
  v:X                IRI-position variable      -> ?X          (v: = <urn:jt:var:>)
  "?x"^^jt:var       literal-position variable  -> ?x
  jt:match / jt:construct / jt:negative (repeatable)  graph names
  jt:filter          spliced SPARQL boolean expression (repeatable)
  jt:bind [jt:seq n; jt:var "x"; jt:expr "..."]       computed value, in jt:seq order
  jt:mint [jt:var v:X; jt:template "urn:...{slot}..."]  IRI from literal variables (ENCODE_FOR_URI)
  jt:derivedFrom     provenance link, written to the prov graph only
Data graphs held in the rule files (mapping data such as a level map or an alignment) are loaded when their
name starts with urn:jt:g: (except urn:jt:g:rules, the rule list).

Usage:
  python3 rulerun.py --rules R.trig [R2.trig ...] --facts F.trig [F2.trig ...] --out OUTDIR \
                     [--output NAME.ttl] [--firing-ns urn:jt:firing:]
Writes OUTDIR/compiled.rq, OUTDIR/<output>, OUTDIR/prov.ttl, OUTDIR/firings.ttl.
Requires rdflib and pyoxigraph.
"""
import argparse
import datetime
from pathlib import Path

import pyoxigraph as ox
import rdflib

JT = "urn:jt:rule-vocab:"
VAR = "urn:jt:var:"
DERIVED = JT + "derivedFrom"
RULES_G = "urn:jt:g:rules"
PROV_G = "urn:jt:g:prov"
FIRINGS_G = "urn:jt:g:firings"
XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"


def term(t):
    if isinstance(t, rdflib.URIRef) and str(t).startswith(VAR):
        return "?" + str(t)[len(VAR):]
    if isinstance(t, rdflib.Literal) and t.datatype == rdflib.URIRef(JT + "var"):
        return "?" + str(t).lstrip("?")
    return t.n3()


def triple(t):
    return " ".join(term(x) for x in t) + " ."


def where_block(triples, tag):
    # every pattern may match in any named graph: the store holds no default-graph data
    return "\n".join(f"  GRAPH ?{tag}{i} {{ {triple(t)} }}" for i, t in enumerate(triples))


class Rules:
    def __init__(self, files):
        self.ds = rdflib.Dataset()
        for f in files:
            self.ds.parse(f, format="trig")
        self.g = self.ds.graph(rdflib.URIRef(RULES_G))

    def p(self, s):
        return rdflib.URIRef(JT + s)

    def triples_of(self, name):
        # sorted, so graph variables (?gl0, ?gn0_0, ...) are numbered the same on every run
        return sorted(self.ds.graph(rdflib.URIRef(str(name))).triples((None, None, None)),
                      key=lambda t: tuple(x.n3() for x in t))

    def ordered(self):
        return sorted(self.g.subjects(rdflib.RDF.type, self.p("Rule")),
                      key=lambda r: int(self.g.value(r, self.p("seq"))))

    def data_graphs(self):
        for ctx in self.ds.graphs():
            name = str(ctx.identifier)
            if name.startswith("urn:jt:g:") and name != RULES_G:
                yield name, ctx

    def compile(self, rule, firing_ns):
        g, p = self.g, self.p
        L = self.triples_of(g.value(rule, p("match")))
        R = self.triples_of(g.value(rule, p("construct")))
        negs = sorted(str(n) for n in g.objects(rule, p("negative")))
        binds = sorted((int(g.value(b, p("seq"))), str(g.value(b, p("var"))), str(g.value(b, p("expr"))))
                       for b in g.objects(rule, p("bind")))
        mints = [(term(g.value(m, p("var"))), str(g.value(m, p("template")))) for m in g.objects(rule, p("mint"))]
        lines = [where_block(L, "gl")]
        for _, var, expr in binds:
            lines.append(f"  BIND({expr} AS ?{var})")
        for var, tpl in mints:
            parts, rest = [], tpl
            while "{" in rest:
                pre, after = rest.split("{", 1)
                slot, rest = after.split("}", 1)
                parts += [rdflib.Literal(pre).n3(), f"ENCODE_FOR_URI(STR(?{slot}))"]
            parts.append(rdflib.Literal(rest).n3())
            lines.append(f"  BIND(IRI(CONCAT({', '.join(parts)})) AS {var})")
        for expr in sorted(str(f) for f in g.objects(rule, p("filter"))):
            lines.append(f"  FILTER({expr})")
        for k, neg in enumerate(negs):
            lines.append("  FILTER NOT EXISTS {\n" + where_block(self.triples_of(neg), f"gn{k}_") + "\n  }")
        firing = f"{firing_ns}{str(rule).rsplit(':', 1)[-1]}"
        out = [t for t in R if str(t[1]) != DERIVED]
        prov = [t for t in R if str(t[1]) == DERIVED]
        insert = f"  GRAPH <{firing}> {{\n" + "\n".join("    " + triple(t) for t in out) + "\n  }"
        if prov:
            insert += f"\n  GRAPH <{PROV_G}> {{\n" + "\n".join("    " + triple(t) for t in prov) + "\n  }"
        return firing, f"INSERT {{\n{insert}\n}}\nWHERE {{\n" + "\n".join(lines) + "\n}"


def to_rdflib(t):
    if isinstance(t, ox.NamedNode):
        return rdflib.URIRef(t.value)
    if isinstance(t, ox.BlankNode):
        return rdflib.BNode(t.value)
    if t.datatype.value == XSD_STRING:          # plain literals, as usdm-rdf asks (no ^^xsd:string)
        return rdflib.Literal(t.value)
    return rdflib.Literal(t.value, datatype=t.datatype.value)


def dump(store, graphs, path):
    g = rdflib.Graph()
    g.bind("usdm", "https://w3id.org/cdisc/usdm/v4/")
    for name in graphs:
        for q in store.quads_for_pattern(None, None, None, ox.NamedNode(name)):
            g.add((to_rdflib(q.subject), to_rdflib(q.predicate), to_rdflib(q.object)))
    g.serialize(str(path), format="turtle")
    return g


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rules", nargs="+", required=True)
    ap.add_argument("--facts", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--output", default="output.ttl")
    ap.add_argument("--firing-ns", default="urn:jt:firing:")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    rules = Rules(a.rules)
    store = ox.Store()
    for f in a.facts:
        store.bulk_load(path=f, format=ox.RdfFormat.TRIG)
    for name, ctx in rules.data_graphs():
        store.bulk_load(input=ctx.serialize(format="nt").encode(), format=ox.RdfFormat.N_TRIPLES,
                        to_graph=ox.NamedNode(name))

    compiled, firings = [], []
    for rule in rules.ordered():
        firing, upd = rules.compile(rule, a.firing_ns)
        label = rules.g.value(rule, rdflib.RDFS.label)
        compiled.append(f"# {label}\n{upd}\n")
        before = len(store)
        store.update(upd)
        added = len(store) - before
        stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        store.update(f"""INSERT DATA {{ GRAPH <{FIRINGS_G}> {{
            <{firing}> a <{JT}Firing> ; <{JT}rule> <{rule}> ;
                <{JT}at> "{stamp}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
                <{JT}quadsAdded> {added} . }} }}""")
        firings.append(firing)
        print(f"{str(rule).rsplit(':', 1)[-1]:4s} +{added:5d} quads  {label}")

    (out / "compiled.rq").write_text("\n".join(compiled))
    result = dump(store, firings, out / a.output)
    dump(store, [PROV_G], out / "prov.ttl")
    dump(store, [FIRINGS_G], out / "firings.ttl")
    print(f"output: {len(result)} triples -> {out / a.output}")


if __name__ == "__main__":
    main()
