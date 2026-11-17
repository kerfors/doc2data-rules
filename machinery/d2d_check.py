"""d2d_check — generic checks over d2d transcripts (TRANSCRIPT-VOCABULARY.md).

  verbatim   IRIs follow the templates; every anchor's oa:exact is on its page in the pinned text layer, and every
             other printed literal (label, heading, number, trailing text) is on one of the element's pages, under
             the run's d2d:textNormalization (label, heading and number on the element's first page);
             d2d:text equals the anchors' exacts joined in page order;
             d2d:withinSection is the nearest section reached through the direct containers.
  structure  against the PDF itself: table parts sit in table cells as the transcript says (one cell each, same row
             = same row band, same column = same column band, order kept, also from one page to the next,
             printed-empty = empty cell, row and column labels in place; a row may continue across a page break;
             a row whose non-empty cells all print the same text is read as one spanning cell, e.g. a row group
             label printed in each column); everything else is printed outside every table (also matched in
             content-stream order, for sub- and superscripts); a section heading is printed right after its number.
  coverage   printed elements no rule used (no jt:derivedFrom points to them).
  drift      each SSSOM row's subject_label equals its element's printed name (label, else heading, else text);
             a row with a match_string (printed co-reference) has a transcript element as object too, and the
             match_string is printed in both elements' names (case-insensitive, nothing else relaxed).
  register   the transcripts' Manifestations are in the register and embody an Expression; the run loads one
             Manifestation per Expression (Q11 guard); the PDF's sha256 and size match the register; at least one of the
             study's registered identifiers is printed on the pinned pages (register vs document).

Usage:
  python3 d2d_check.py verbatim  --transcript T.trig [...] --text-layer F.txt [...]
  python3 d2d_check.py structure --transcript T.trig [...] --pdf FILE.pdf --marker-fonts Symbol CourierNew
  python3 d2d_check.py coverage  --transcript T.trig [...] --prov prov.ttl [...]
  python3 d2d_check.py drift     --transcript T.trig [...] --sssom M.sssom.tsv [...]
  python3 d2d_check.py register  --transcript T.trig [...] --register R.trig --pdf FILE.pdf --text-layer F.txt [...]
Exit status 1 when a check fails. Requires rdflib; structure also pdfplumber; drift also pandas and pyyaml.
"""
import argparse
import re
import sys
from pathlib import Path

import rdflib
from rdflib.namespace import RDF

sys.path.insert(0, str(Path(__file__).parent))
import d2d_iri  # noqa: E402

D2D = rdflib.Namespace("urn:jt:d2d:")
OA = rdflib.Namespace("http://www.w3.org/ns/oa#")
PROV = rdflib.Namespace("http://www.w3.org/ns/prov#")
DCT = rdflib.Namespace("http://purl.org/dc/terms/")
OBO = rdflib.Namespace("http://purl.obolibrary.org/obo/")
DERIVED = rdflib.URIRef("urn:jt:rule-vocab:derivedFrom")
RFC3778 = rdflib.URIRef("http://tools.ietf.org/rfc/rfc3778")
TABLE, CAPTION = OBO.IAO_0000306, OBO.IAO_0000304
FRBR = rdflib.Namespace("http://purl.org/vocab/frbr/core#")
PART_OF = [D2D.inSection, D2D.inTable, D2D.inRowGroup, D2D.inRow, D2D.inColumn, D2D.inCell, D2D.inList,
           D2D.inListItem]
CONTENT_OF = [D2D.inCell, D2D.inList, D2D.inListItem]       # parts that make up a cell's printed content
PRINTED = [D2D.text, D2D.label, D2D.heading, D2D.number, D2D.trailingText]
NORMALIZATIONS = {D2D.whitespaceCollapsed: lambda s: re.sub(r"\s+", " ", s).strip()}
TOL = 1.0                                                   # points, for row and column bands
RULE = 1.5                                                  # points: a filled rectangle this thin or thinner is a rule


def nows(s):
    return re.sub(r"\s+", "", s)


class Transcripts:
    def __init__(self, files):
        self.ds = rdflib.Dataset()
        for f in files:
            self.ds.parse(f, format="trig")
        self.u = rdflib.Graph()
        for g in self.ds.graphs():
            self.u += g
        self.graphs = sorted({s for s in self.u.subjects(PROV.wasGeneratedBy, None)
                              if len(self.ds.graph(s)) > 0})
        if not self.graphs:
            sys.exit("no transcript graph (a named graph with prov:wasGeneratedBy) in the input")

    def elements(self, tg):
        return sorted(self.ds.graph(tg).subjects(D2D.localId, None))

    def one(self, s, p):
        vals = list(self.u.objects(s, p))
        if len(vals) != 1:
            sys.exit(f"{s} needs exactly one {p}, has {len(vals)}")
        return vals[0]

    def opt(self, s, p):
        vals = list(self.u.objects(s, p))
        if len(vals) > 1:
            sys.exit(f"{s} has more than one {p}")
        return vals[0] if vals else None

    def run(self, tg):
        r = self.one(tg, PROV.wasGeneratedBy)
        n = self.one(r, D2D.textNormalization)
        if n not in NORMALIZATIONS:
            sys.exit(f"{r}: unknown d2d:textNormalization {n}")
        return r, NORMALIZATIONS[n]

    def pages(self, e, m):
        out = []
        for p in self.u.objects(e, D2D.onPage):
            n = int(self.one(p, D2D.pageIndex))
            if str(p) != d2d_iri.page_iri(m, n):
                sys.exit(f"{e}: page IRI {p} does not follow {{M}}/page/{{n}} for page {n}")
            out.append(n)
        return sorted(out)

    def anchors(self, e, m):
        """[(page, exact or None)] in anchor order; checks the anchor IRIs and selectors."""
        out = []
        for k, a in enumerate(sorted(self.u.objects(e, D2D.anchor), key=lambda a: int(str(a).rsplit("/", 1)[1])), 1):
            if str(a) != d2d_iri.anchor_iri(str(e), k):
                sys.exit(f"{e}: anchor {a} is not {{element}}/anchor/{k}")
            if self.one(a, OA.hasSource) != rdflib.URIRef(m):
                sys.exit(f"{a}: oa:hasSource is not the Manifestation {m}")
            fs = self.one(a, OA.hasSelector)
            if self.one(fs, DCT.conformsTo) != RFC3778:
                sys.exit(f"{a}: FragmentSelector does not conform to RFC 3778")
            val = str(self.one(fs, RDF.value))
            if not re.fullmatch(r"page=[1-9][0-9]*", val):
                sys.exit(f"{a}: fragment {val!r} is not page=N")
            tq = self.opt(fs, OA.refinedBy)
            out.append((int(val[5:]), str(self.one(tq, OA.exact)) if tq is not None else None))
        return out

    def printed(self, e):
        return any(self.u.value(e, p) is not None for p in PRINTED) or self.u.value(e, D2D.anchor) is not None

    def order(self, e):
        o = self.u.value(e, D2D.order)
        return int(o) if o is not None else 0

    def children(self, tg, x, props):
        g = self.ds.graph(tg)
        kids = {s for p in props for s in g.subjects(p, x)}
        return sorted(kids, key=self.order)

    def in_table(self, tg, e):
        """The table an element is part of, or None."""
        seen, todo = set(), [e]
        while todo:
            x = todo.pop()
            if (x, RDF.type, TABLE) in self.u:
                return x
            seen.add(x)
            todo += [o for p in PART_OF for o in self.u.objects(x, p) if o not in seen]
        return None

    def in_cell(self, e):
        """True for a cell, and for anything that is printed content of a cell (via inCell/inList/inListItem)."""
        if (e, RDF.type, D2D.Cell) in self.u:
            return True
        return any(self.in_cell(x) for p in CONTENT_OF for x in self.u.objects(e, p))

    def nearest_section(self, e):
        """The nearest section reached upward through direct containers (PART_OF), or None; fails if two."""
        level, seen = [e], {e}
        while level:
            up = {o for x in level for p in PART_OF for o in self.u.objects(x, p)} - seen
            secs = {o for o in up if (o, RDF.type, D2D.Section) in self.u}
            if len(secs) > 1:
                sys.exit(f"{e}: two nearest sections {sorted(secs)}")
            if secs:
                return secs.pop()
            seen |= up
            level = up
        return None

    def name(self, e):
        for p in (D2D.label, D2D.heading, D2D.text):
            v = self.u.value(e, p)
            if v is not None:
                return str(v)
        return None


def load_text_layers(t, tg, paths):
    run, _ = t.run(tg)
    by_hex = {d2d_iri.sha256_file(p): p for p in paths}
    pages = {}
    layers = [f for f in t.u.objects(run, PROV.used) if t.u.value(f, D2D.firstPageIndex) is not None]
    if not layers:
        sys.exit(f"{run}: no prov:used text layer (an entity with d2d:firstPageIndex)")
    for f in layers:
        hexd = str(f).rsplit("/", 1)[1]
        if str(f) != d2d_iri.file_iri(hexd):
            sys.exit(f"{f}: text layer IRI is not {{B}}sha256/{{hex}}")
        if hexd not in by_hex:
            sys.exit(f"{run} used text layer {hexd}, not among the --text-layer files given")
        parts = Path(by_hex[hexd]).read_text(encoding="utf-8").split("\f")
        if parts[-1] != "":
            sys.exit(f"{by_hex[hexd]}: does not end with a form feed (pdftotext page break)")
        first = int(t.u.value(f, D2D.firstPageIndex))
        for i, txt in enumerate(parts[:-1]):
            if pages.setdefault(first + i, txt) != txt:
                sys.exit(f"page {first + i} differs between text layers")
    return pages


def verbatim(a):
    t = Transcripts(a.transcript)
    fails = []
    for tg in t.graphs:
        m = d2d_iri.manifestation_of(str(tg))
        if str(tg) != d2d_iri.transcript_iri(m, str(tg).rsplit("/", 1)[1]):
            sys.exit(f"{tg}: transcript graph IRI is not {{M}}/transcript/{{name}}")
        run, norm = t.run(tg)
        pages = load_text_layers(t, tg, a.text_layer)
        npages = {n: norm(txt) for n, txt in pages.items()}
        n_el = n_anchor = n_lit = 0
        for e in t.elements(tg):
            n_el += 1
            m2, _, lid = d2d_iri.split_element(str(e))
            if m2 != m or lid != str(t.one(e, D2D.localId)):
                fails.append(f"{lid}: IRI {e} does not match {{M}}/{{producer}}/{{localId}}")
            want = t.nearest_section(e)
            have = set(t.u.objects(e, D2D.withinSection))
            if have != ({want} if want is not None else set()):
                fails.append(f"{lid}: d2d:withinSection {sorted(str(x).rsplit('/', 1)[1] for x in have)}, "
                             f"nearest section by containment "
                             f"{str(want).rsplit('/', 1)[1] if want is not None else 'none'}")
            on = t.pages(e, m)
            anchors = t.anchors(e, m)
            text = t.u.value(e, D2D.text)
            empty = t.u.value(e, D2D.printedEmpty)
            if t.printed(e) and not on:
                fails.append(f"{lid}: printed but no d2d:onPage")
            if text is not None or empty is not None:
                if [p for p, _ in anchors] != on:
                    fails.append(f"{lid}: anchors on pages {[p for p, _ in anchors]}, d2d:onPage {on}")
            for p, exact in anchors:
                n_anchor += 1
                if exact is None:
                    continue
                if norm(exact) != exact:
                    fails.append(f"{lid}: oa:exact on page {p} is not normalized: {exact!r}")
                if p not in npages:
                    fails.append(f"{lid}: page {p} is not in the text layer")
                elif exact not in npages[p]:
                    fails.append(f"{lid}: not on page {p}: {exact!r}")
            if empty is not None and empty.toPython() is True:
                if text is not None or any(x is not None for _, x in anchors):
                    fails.append(f"{lid}: printed empty, but has text")
            elif text is not None:
                joined = " ".join(x for _, x in anchors if x is not None)
                if str(text) != joined:
                    fails.append(f"{lid}: d2d:text differs from its anchors' exacts: {str(text)!r} vs {joined!r}")
            for p in (D2D.label, D2D.heading, D2D.number, D2D.trailingText):
                where = on if p == D2D.trailingText else on[:1]
                for lit in t.u.objects(e, p):
                    n_lit += 1
                    s = str(lit)
                    if norm(s) != s:
                        fails.append(f"{lid}: {p.split(':')[-1]} not normalized: {s!r}")
                    elif not any(n in npages and s in npages[n] for n in where):
                        fails.append(f"{lid}: {p.split(':')[-1]} not on page(s) {where}: {s!r}")
        print(f"{tg}\n  run {run}\n  text layer pages {sorted(pages)}\n"
              f"  {n_el} elements, {n_anchor} anchors, {n_lit} other printed literals")
    report(fails, "verbatim")


def report(fails, what):
    for f in fails:
        print("  FAIL", f)
    print(f"{what}: {'FAILED, ' + str(len(fails)) + ' problem(s)' if fails else 'ok'}")
    if fails:
        sys.exit(1)


# ------------------------------------------------------------------------------------------------ structure

def inside(b, outer):
    return b[0] >= outer[0] - TOL and b[1] >= outer[1] - TOL and b[2] <= outer[2] + TOL and b[3] <= outer[3] + TOL


def font(c):
    return c.get("fontname", "").split("+")[-1]


def shading(o):
    """A filled rectangle thicker than a rule and not black (grey or RGB fill above 0): background shading, which
    bounds no cell. Black boxes (redactions) are kept: they can close a rule they cover."""
    if o["object_type"] != "rect" or min(o["width"], o["height"]) <= RULE:
        return False
    c = o["non_stroking_color"]
    v = list(c) if isinstance(c, (list, tuple)) else [c]
    return len(v) in (1, 3) and all(x is not None and x > 0 for x in v)


def centre_in(o, bbox):
    if "x0" not in o:
        return False
    x, y = (o["x0"] + o["x1"]) / 2, (o["top"] + o["bottom"]) / 2
    return bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]


def region_text(page, bbox, markers):
    """Text of the characters whose centre lies in bbox, without list-marker fonts, whitespace removed."""
    return nows(page.filter(lambda o: centre_in(o, bbox) and font(o) not in markers).extract_text() or "")


def strings_on(t, e, m, n):
    """The element's own printed strings on page n (anchor exacts; label, heading, number on its first page)."""
    out = [x for p, x in t.anchors(e, m) if p == n and x is not None]
    if t.pages(e, m)[:1] == [n]:
        out += [str(v) for p in (D2D.label, D2D.heading, D2D.number) for v in t.u.objects(e, p)]
    return out


def cell_content(t, tg, e, m, n):
    s = "".join(x for p, x in t.anchors(e, m) if p == n and x is not None)
    for k in t.children(tg, e, CONTENT_OF):
        s += cell_content(t, tg, k, m, n)
    tail = t.u.value(e, D2D.trailingText)
    if tail is not None:
        on = t.pages(e, m)
        if len(on) != 1:
            sys.exit(f"{e}: trailing text on an element printed across pages is not handled in v0")
        if on == [n]:
            s += str(tail)
    return nows(s)


def merge_repeated_rows(cells):
    """A ruled row band whose non-empty cells (two or more) all print the same text is read as one cell spanning
    them (a row group label printed in each column). Empty cells in the band (shading slivers) are left as they are.
    Returns the merged cells and the merged texts."""
    bands = {}
    for b in cells:
        key = next((k for k in bands if abs(k[0] - b[1]) <= TOL and abs(k[1] - b[3]) <= TOL), (b[1], b[3]))
        bands.setdefault(key, []).append(b)
    out, merged = dict(cells), []
    for bs in bands.values():
        bs = [b for b in bs if cells[b] != ""]
        texts = {cells[b] for b in bs}
        if len(bs) > 1 and len(texts) == 1:
            for b in bs:
                del out[b]
            out[(min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))] = \
                texts.pop()
            merged.append(cells[bs[0]])
    return out, merged


def columns_of(t, c):
    """The columns a cell is printed in, in column order: one, or more for a cell printed across columns."""
    cols = sorted(t.u.objects(c, D2D.inColumn), key=t.order)
    if not cols:
        sys.exit(f"{c} has no d2d:inColumn")
    return tuple(cols)


def table_items(t, tg, tab, m, n):
    """What the transcript places in a table on page n: cells, row labels, column labels, row group labels."""
    on = lambda x: n in t.pages(x, m)
    first = lambda x: t.pages(x, m)[:1] == [n]
    groups = [g for g in t.children(tg, tab, [D2D.inTable]) if (g, RDF.type, D2D.RowGroup) in t.u]
    cols = [c for c in t.children(tg, tab, [D2D.inTable]) if (c, RDF.type, D2D.Column) in t.u]
    loose = [r for r in t.children(tg, tab, [D2D.inTable]) if (r, RDF.type, D2D.Row) in t.u]
    if groups and loose:
        sys.exit(f"{tab}: rows both in and outside row groups is not handled in v0")
    rows = [(r, (t.order(g), t.order(r))) for g in groups for r in t.children(tg, g, [D2D.inRowGroup])]
    rows += [(r, (0, t.order(r))) for r in loose]
    items = []
    for g in groups:
        if first(g) and t.u.value(g, D2D.label) is not None:
            items.append(dict(el=g, kind="grouplabel", row=("g", g), key=(t.order(g), 0), col=None,
                              want=nows(str(t.u.value(g, D2D.label)))))
    for c in cols:
        if first(c) and t.u.value(c, D2D.label) is not None:
            items.append(dict(el=c, kind="collabel", row=("c", c), key=(-1, 0), col=(c,),
                              want=nows(str(t.u.value(c, D2D.label)))))
    for r, key in rows:
        if not on(r):
            continue
        if first(r) and t.u.value(r, D2D.label) is not None:
            items.append(dict(el=r, kind="rowlabel", row=r, key=key, col=None, want=nows(str(t.u.value(r, D2D.label)))))
        for c in t.children(tg, r, [D2D.inRow]):
            if on(c):
                items.append(dict(el=c, kind="cell", row=r, key=key, col=columns_of(t, c),
                                  want=cell_content(t, tg, c, m, n)))
    corder = {c: t.order(c) for c in cols}
    return items, corder


def consistent(i, a, j, b, corder):
    """Can item i sit in pdf cell a while item j sits in pdf cell b?"""
    if a == b:
        return False
    ya, yb = (a[1], a[3]), (b[1], b[3])
    xa, xb = (a[0], a[2]), (b[0], b[2])
    band = lambda u, v: abs(u[0] - v[0]) <= TOL and abs(u[1] - v[1]) <= TOL
    if i["row"] == j["row"]:
        if i["kind"] in ("cell", "rowlabel") and j["kind"] in ("cell", "rowlabel") and not band(ya, yb):
            return False
        if i["kind"] == "rowlabel" and j["kind"] == "cell" and xa[1] > xb[0] + TOL:
            return False
        if j["kind"] == "rowlabel" and i["kind"] == "cell" and xb[1] > xa[0] + TOL:
            return False
    elif i["key"] != j["key"] or i["kind"] == "collabel" or j["kind"] == "collabel":
        if i["key"] < j["key"] and ya[1] > yb[0] + TOL:
            return False
        if j["key"] < i["key"] and yb[1] > ya[0] + TOL:
            return False
    if i["col"] is not None and j["col"] is not None:
        (lo_i, hi_i), (lo_j, hi_j) = [(min(corder[c] for c in x["col"]), max(corder[c] for c in x["col"])) for x in (i, j)]
        if set(i["col"]) == set(j["col"]):
            if not band(xa, xb):
                return False
        elif set(i["col"]) & set(j["col"]):                 # a cell printed across columns: edges in column order
            for (u, v), (p, q) in (((lo_i, lo_j), (xa[0], xb[0])), ((hi_i, hi_j), (xa[1], xb[1]))):
                if (u == v and abs(p - q) > TOL) or (u < v and p > q - TOL) or (u > v and p < q + TOL):
                    return False
        elif i["kind"] == "cell" and j["kind"] == "cell":
            if hi_i < lo_j and xa[1] > xb[0] + TOL:
                return False
            if hi_j < lo_i and xb[1] > xa[0] + TOL:
                return False
    return True


def solve(items, cells, corder, limit=2):
    cand = [[b for b, txt in cells.items() if txt == it["want"]] for it in items]
    idx = sorted(range(len(items)), key=lambda k: len(cand[k]))
    sols, chosen = [], {}

    def go(d):
        if len(sols) >= limit:
            return
        if d == len(idx):
            sols.append(dict(chosen))
            return
        k = idx[d]
        for b in cand[k]:
            if all(consistent(items[k], b, items[j], bj, corder) for j, bj in chosen.items()):
                chosen[k] = b
                go(d + 1)
                del chosen[k]

    go(0)
    return sols, cand


def structure(a):
    import pdfplumber
    t = Transcripts(a.transcript)
    hexd = d2d_iri.sha256_file(a.pdf)
    m = d2d_iri.file_iri(hexd)
    graphs = [tg for tg in t.graphs if d2d_iri.manifestation_of(str(tg)) == m]
    if not graphs:
        sys.exit(f"no transcript graph under the PDF's Manifestation {m}")
    markers = set(a.marker_fonts)
    fails = []
    pdf = pdfplumber.open(a.pdf)
    for tg in graphs:
        print(tg)
        spans = {}                                      # table -> [(page, lowest row key, highest row key)]
        els = t.elements(tg)
        if any((e, RDF.type, CAPTION) in t.u for e in els):
            sys.exit("caption check not implemented in v0: no real caption seen yet")
        for n in sorted({p for e in els for p in t.pages(e, m)}):
            page = pdf.pages[n - 1]
            ruled = page.filter(lambda o: not shading(o))
            found = ruled.find_tables({"vertical_strategy": "lines", "horizontal_strategy": "lines"})
            outer = [x for x in found if not any(y is not x and inside(x.bbox, y.bbox) for y in found)]
            inner = [x for x in found if x not in outer]
            out_text_page = page.filter(lambda o: not any(centre_in(o, x.bbox) for x in outer))
            outside = nows(out_text_page.extract_text() or "")
            outside_flow = nows(out_text_page.extract_text(use_text_flow=True) or "")   # sub/superscripts in place
            print(f"  page {n}: {len(outer)} table region(s) {[tuple(round(v, 1) for v in x.bbox) for x in outer]}"
                  + (f", {len(inner)} ruled region(s) inside them, ignored" if inner else ""))
            used_regions = set()
            for tab in [e for e in els if (e, RDF.type, TABLE) in t.u and n in t.pages(e, m)]:
                lid = str(t.one(tab, D2D.localId))
                items, corder = table_items(t, tg, tab, m, n)
                hits = []
                for ri, reg in enumerate(outer):
                    cells = {}
                    for row in reg.rows:
                        for b in row.cells:
                            if b is not None:
                                cells[tuple(b)] = region_text(page, b, markers)
                    cells, merged = merge_repeated_rows(cells)
                    for txt in merged:
                        print(f"    region {ri}: a row prints {txt!r} in each of its non-empty cells, "
                              f"read as one spanning cell")
                    sols, cand = solve(items, cells, corder)
                    hits.append((ri, sols, cand, cells))
                good = [h for h in hits if h[1]]
                if len(good) != 1 or len(good[0][1]) != 1:
                    fails.append(f"{lid} p.{n}: " + ("no table region fits the transcript" if not good else
                                 f"{sum(len(h[1]) for h in good)} placements fit, not exactly one"))
                    if not good and len(outer) == 1:
                        missing = [it for k, it in enumerate(items) if not hits[0][2][k]]
                        for it in missing:
                            fails.append(f"  no cell prints {t.u.value(it['el'], D2D.localId)} "
                                         f"({it['kind']}): {it['want']!r}")
                        if not missing:
                            fails.append("  every item has a cell with its text, but no placement keeps rows, "
                                         "columns and their order consistent")
                    continue
                ri, sols, _, cells = good[0]
                used_regions.add(ri)
                sol = sols[0]
                keys = [items[k]["key"] for k in sol if items[k]["kind"] in ("cell", "rowlabel")]
                if keys:
                    spans.setdefault(tab, []).append((n, min(keys), max(keys)))
                print(f"    {lid}: {len(items)} items placed in region {ri} "
                      f"({sum(1 for i in items if i['kind'] == 'cell')} cells, "
                      f"{sum(1 for i in items if i['want'] == '')} printed empty)")
                for k in sorted(sol, key=lambda k: (sol[k][1], sol[k][0])):
                    it = items[k]
                    print(f"      {str(t.u.value(it['el'], D2D.localId)):10s} {it['kind']:10s} "
                          f"x {sol[k][0]:6.1f}-{sol[k][2]:6.1f}  y {sol[k][1]:6.1f}-{sol[k][3]:6.1f}")
                rest = [b for b, txt in cells.items() if txt and b not in sol.values()]
                for b in rest:
                    print(f"      not in the transcript: cell y {b[1]:.1f} x {b[0]:.1f}: {cells[b][:60]!r}")
                # other parts of this table (not cells, not labels): inside the region
                reg_text = region_text(page, outer[ri].bbox, set())
                placed = {it["el"] for it in items}
                for e in els:
                    if e in placed or t.in_table(tg, e) != tab or t.in_cell(e):
                        continue
                    for s in strings_on(t, e, m, n):
                        if nows(s) not in reg_text:
                            fails.append(f"{t.u.value(e, D2D.localId)} p.{n}: part of {lid}, not printed inside "
                                         f"its table region: {s!r}")
            for e in els:
                if t.in_table(tg, e) is not None:
                    continue
                lid = str(t.u.value(e, D2D.localId))
                for s in strings_on(t, e, m, n):
                    if nows(s) in outside or nows(s) in outside_flow:
                        continue
                    where = "inside a table region" if any(
                        nows(s) in region_text(page, x.bbox, set()) for x in outer) else "nowhere in the page geometry"
                    fails.append(f"{lid} p.{n}: not part of a table, but printed {where}: {s!r}")
                num, head = t.u.value(e, D2D.number), t.u.value(e, D2D.heading)
                if (e, RDF.type, D2D.Section) in t.u and num is not None and head is not None \
                        and t.pages(e, m)[:1] == [n]:
                    lines = [nows(x) for x in (out_text_page.extract_text() or "").split("\n")]
                    want = (nows(str(num)), nows(str(head)))
                    ok = any(lines[i].startswith(want[0]) and
                             re.match(re.escape(want[0]) + r"\.?" + re.escape(want[1]), "".join(lines[i:i + 3]))
                             for i in range(len(lines)))
                    print(f"    {lid}: heading after number {str(num)!r} on one line: {'yes' if ok else 'NO'}")
                    if not ok:
                        fails.append(f"{lid} p.{n}: heading {str(head)!r} is not printed after number {str(num)!r}")
        for tab, sp in spans.items():
            sp.sort()
            for (n1, _, hi), (n2, lo, _) in zip(sp, sp[1:]):
                if hi > lo:
                    fails.append(f"{t.u.value(tab, D2D.localId)}: rows on p.{n2} do not follow the rows on p.{n1} "
                                 f"in row group and row order (a row may continue across the break)")
    report(fails, "structure")


# ------------------------------------------------------------------------------------------------ coverage, drift

def coverage(a):
    t = Transcripts(a.transcript)
    used = set()
    for f in a.prov:
        g = rdflib.Graph()
        g.parse(f)
        used |= set(g.objects(None, DERIVED))
    for tg in t.graphs:
        printed = [e for e in t.elements(tg) if t.printed(e)]
        unused = [e for e in printed if e not in used]
        print(f"{tg}: {len(printed)} printed elements, {len(printed) - len(unused)} used by a rule, "
              f"{len(unused)} not used")
        for e in unused:
            kinds = ",".join(sorted(str(c).rsplit(":", 1)[-1].rsplit("/", 1)[-1] for c in t.u.objects(e, RDF.type)))
            print(f"  {str(t.u.value(e, D2D.localId)):12s} {kinds:28s} {(t.name(e) or '')[:80]!r}")


def drift(a):
    import pandas as pd
    import yaml
    t = Transcripts(a.transcript)
    elements = {e for tg in t.graphs for e in t.elements(tg)}
    fails, n = [], 0
    for f in a.sssom:
        lines = Path(f).read_text(encoding="utf-8").splitlines()
        cmap = yaml.safe_load("\n".join(x[1:] for x in lines if x.startswith("#")))["curie_map"]
        df = pd.read_csv(f, sep="\t", comment="#", dtype=str, keep_default_na=False)
        for _, r in df.iterrows():
            n += 1
            p, local = r["subject_id"].split(":", 1)
            s = rdflib.URIRef(cmap[p] + local)
            if s not in elements:
                fails.append(f"{r['record_id']}: subject {s} is not a transcript element")
                continue
            name = t.name(s)
            if name is None:
                fails.append(f"{r['record_id']}: subject {t.u.value(s, D2D.localId)} has no printed name")
            elif name != r["subject_label"]:
                fails.append(f"{r['record_id']}: subject_label {r['subject_label']!r} != printed {name!r}")
            if r.get("match_string", ""):
                p, local = r["object_id"].split(":", 1)
                o = rdflib.URIRef(cmap[p] + local)
                if o not in elements:
                    fails.append(f"{r['record_id']}: match_string row, object {o} is not a transcript element")
                    continue
                oname = t.name(o)
                m = r["match_string"].casefold()
                for side, text in (("subject", name), ("object", oname)):
                    if text is None or m not in text.casefold():
                        fails.append(f"{r['record_id']}: match_string {r['match_string']!r} not printed in {side}")
    print(f"{n} mapping rows checked")
    report(fails, "drift")


def register(a):
    t = Transcripts(a.transcript)
    reg = rdflib.Dataset()
    reg.parse(a.register, format="trig")
    r = rdflib.Graph()
    for g in reg.graphs():
        r += g
    fails = []
    by_expr, mans = {}, set()
    for tg in t.graphs:
        m = rdflib.URIRef(d2d_iri.manifestation_of(str(tg)))
        mans.add(m)
        exprs = list(r.objects(m, FRBR.embodimentOf))
        if not exprs:
            fails.append(f"{tg}: Manifestation {m} is not in the register")
        for e in exprs:
            by_expr.setdefault(e, set()).add(m)
    for e, ms in by_expr.items():
        if len(ms) > 1:
            fails.append(f"{e}: the run loads transcripts of {len(ms)} Manifestations of one Expression: {sorted(ms)}")
    hexd = d2d_iri.sha256_file(a.pdf)
    m = rdflib.URIRef(d2d_iri.file_iri(hexd))
    if m not in mans:
        sys.exit(f"{a.pdf}: sha256 {hexd} is not the Manifestation of any transcript given")
    size = r.value(m, D2D.byteSize)
    if size is None or int(size) != Path(a.pdf).stat().st_size:
        fails.append(f"{a.pdf}: {Path(a.pdf).stat().st_size} bytes, register says {size}")
    norm = NORMALIZATIONS[D2D.whitespaceCollapsed]
    for e in r.objects(m, FRBR.embodimentOf):
        w = r.value(e, FRBR.realizationOf)
        s = r.value(w, OBO.IAO_0000136)
        ids = [(str(r.value(n, D2D.idField)), str(r.value(n, D2D.idValue))) for n in r.objects(s, D2D.registeredId)]
        pages = {}
        for tg in t.graphs:
            if rdflib.URIRef(d2d_iri.manifestation_of(str(tg))) == m:
                pages.update({n: norm(x) for n, x in load_text_layers(t, tg, a.text_layer).items()})
        print(f"{m}\n  embodies {e}, realization of {w}, about {s}\n  pinned pages {sorted(pages)}")
        found = 0
        for field, value in sorted(ids):
            hits = [n for n in sorted(pages) if value in pages[n]]
            found += bool(hits)
            print(f"    {field:18s} {value:20s} printed on {len(hits)} of {len(pages)} pinned pages")
        if not found:
            fails.append(f"{m}: none of the study's registered identifiers is printed on the pinned pages")
    report(fails, "register")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="check", required=True)
    for name, extra in (("verbatim", [("--text-layer", {})]),
                        ("structure", [("--pdf", {"nargs": None}), ("--marker-fonts", {})]),
                        ("coverage", [("--prov", {})]),
                        ("drift", [("--sssom", {})]),
                        ("register", [("--register", {"nargs": None}), ("--pdf", {"nargs": None}),
                                      ("--text-layer", {})])):
        p = sub.add_parser(name)
        p.add_argument("--transcript", nargs="+", required=True)
        for flag, kw in extra:
            p.add_argument(flag, nargs=kw.get("nargs", "+"), required=True)
    a = ap.parse_args()
    {"verbatim": verbatim, "structure": structure, "coverage": coverage, "drift": drift,
     "register": register}[a.check](a)


if __name__ == "__main__":
    main()
