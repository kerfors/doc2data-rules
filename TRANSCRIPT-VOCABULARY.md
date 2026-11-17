# The d2d transcript vocabulary (v0, draft)

A transcript says what a document prints and where, with no decisions. Rules (`jt:`, VOCABULARY.md) read
transcripts; mapping data and output are separate graphs. This page describes the vocabulary in
`vocab/d2d.ttl`, the IRI scheme every producer uses, how elements anchor to pages and printed text, and how a
transcript run is recorded.

## Vocabularies used

| Concern | Vocabulary |
|---|---|
| Document identity: Work, Expression, Manifestation | FRBR Core (`http://purl.org/vocab/frbr/core#`) |
| Element types | IAO (release 2026-03-30), with our own classes where IAO has none; DoCO as `skos:closeMatch` only |
| Containment | BFO part of (`obo:BFO_0000050`), via our subproperties |
| Anchors | W3C Web Annotation selectors, without `oa:Annotation` |
| How a transcript was made | PROV-O |

Why own classes: IAO has document, document part, textual entity, table, figure, footnote, caption and
abbreviation textual entity, but no generic section, paragraph, sentence, list, row, column, cell or page.
DoCO (v1.4.1) has section, paragraph, sentence and list, but not page, row, column, cell, list item or row
group, and subclassing it would bring in the Pattern Ontology's axioms. So d2d classes sit under IAO, which
keeps transcripts BFO-compliant, and point to DoCO with `skos:closeMatch`.

## Classes

| Class | Superclass | For |
|---|---|---|
| `d2d:Section` | IAO document part | a division under a printed heading; number optional; sections nest |
| `d2d:List` | IAO document part | a bulleted or numbered list |
| `d2d:Row`, `d2d:Column` | IAO document part | a printed table row / column |
| `d2d:RowGroup` | IAO document part | rows under one spanning label row (a band) |
| `d2d:Page` | IAO document part | the content as laid out on one physical page of a Manifestation |
| `d2d:Paragraph`, `d2d:Sentence` | IAO textual entity | running text |
| `d2d:ListItem`, `d2d:ListLead` | IAO textual entity | one item; the text that introduces a list |
| `d2d:LabelledItem` | IAO textual entity | text printed as "label: value" |
| `d2d:Cell` | IAO textual entity | a table cell, possibly printed empty |
| IAO table, figure, footnote, caption, document title, abbreviation textual entity | — | used directly |

An element may have more than one type when one printed unit is both: a bullet printed as "label: value" is a
`d2d:ListItem` and a `d2d:LabelledItem`; a sentence that introduces a list is a `d2d:Sentence` and a
`d2d:ListLead`. The types say what the unit is; no flag records how it is laid out.

## Properties

- Containment, all subproperties of BFO part of: `d2d:inSection`, `inTable`, `inRowGroup`, `inRow`,
  `inColumn`, `inCell`, `inList`, `inListItem`, `onPage`. Rules use the specific property; generic tools
  list them all, since `rulerun.py` does no inference. These point to the direct container. A cell printed across
  columns has one `d2d:inColumn` per column.
- `d2d:withinSection` (also a subproperty of BFO part of): the nearest section the element is printed in,
  stated on every element inside a section. Rules use it to reach an element by its section whether it is
  printed in a list, a table or directly in the section. It follows from the direct containment, and the
  verbatim check recomputes it.
- Printed values: `d2d:text`, `trailingText`, `heading`, `number` (as printed, a string), `label`,
  `printedEmpty`, `order` (from 1, reading order within the container).
- Pages and files: `d2d:pageIndex` (physical page, from 1), `d2d:pageLabel` (as printed), `d2d:sha256`,
  `d2d:firstPageIndex` (on a text-layer file: the physical page its first page is).
- `d2d:localId`: the producer's id of the element; the last segment of its IRI.
- `d2d:anchor`: see below.

## IRIs

`{B}` is the base. In files today `{B}` = `urn:jt:`; later it becomes
`https://w3id.org/people/kerfors/doc2data/`. The vocabulary namespace `urn:jt:d2d:` becomes
`https://w3id.org/people/kerfors/doc2data/d2d#`.

| Node | IRI | Minted by |
|---|---|---|
| File (any input) | `{B}sha256/{hex}` | anyone holding the bytes |
| Manifestation | the file's IRI, typed `frbr:Manifestation` | anyone holding the bytes |
| Page | `{M}/page/{n}`, n = physical page from 1 | anyone holding the bytes |
| Transcript element | `{M}/{producer}/{localId}` | the producer |
| Anchor | `{element}/anchor/{k}` | the producer |
| Transcript graph | `{M}/transcript/{name}` | the producer |
| Study | `{B}study/s{nnnn}` | the register |
| Work | `{B}work/w{nnnn}` | the register |
| Expression | `{B}expr/e{nnnn}` | the register |

Rules for the hash and the base:
- `{hex}` = SHA-256 of the **file of record**, all 64 characters, lowercase, no normalization: the file as
  published (for example as downloaded from ClinicalTrials.gov), or the rendition in the document management
  system, not a personal or watermarked copy.
- Nothing under `{M}` can change, because the bytes cannot. A new version is a new Manifestation with new
  element IRIs; "same section in two versions" is a rule's reading, not an identity.
- "Same document" is said in the register (`frbr:embodimentOf` from Manifestation to Expression,
  `frbr:realizationOf` from Expression to Work), never in an IRI. A combined file (protocol and SAP) is one
  Manifestation embodying two Expressions.
- The base follows the document's world, not the producer: public documents under the public base, internal
  documents under an internal base. A pipeline that uses a public document uses its public IRIs.

Producers: each producer (`d2d`, `soa2usdm`, …) owns the ids in its own segment under `{M}` and its own
subclasses. Producers meet at page IRIs and through layer 2 links; a shared layout path was rejected
because producers segment pages differently.

## Anchors

Rules read `d2d:text` and `d2d:onPage` on the element. The anchor is for verification tools. It is an IRI,
not a blank node: `rulerun.py` puts each match triple in its own `GRAPH` pattern, and SPARQL does not allow
one blank node label across several of them.

```turtle
<{M}/d2d/{localId}> d2d:text "…" ;
    d2d:onPage <{M}/page/{n}> ;
    d2d:anchor <{M}/d2d/{localId}/anchor/1> .

<{M}/d2d/{localId}/anchor/1> a oa:SpecificResource ;
    oa:hasSource <{M}> ;
    oa:hasSelector [ a oa:FragmentSelector ;
        dcterms:conformsTo <http://tools.ietf.org/rfc/rfc3778> ;
        rdf:value "page={n}" ;
        oa:refinedBy [ a oa:TextQuoteSelector ; oa:exact "…" ] ] .
```

- `d2d:onPage` lists every page an element is printed on, containers included (a table, a section, a column
  that runs over a page break). An element printed across pages has one anchor per page.
- A label, heading or number is printed on the element's first page (a column header, a row group label, a
  section heading); the checks look for it there.
- A cell printed empty has `d2d:printedEmpty true` and an anchor without a TextQuoteSelector.
- Strings are stored normalized, under the run's `d2d:textNormalization` (v0: `d2d:whitespaceCollapsed`).
  So `oa:exact` is the printed characters with whitespace collapsed, not the raw characters.
- `d2d:text` and the anchors are both kept. For an element on one page, `d2d:text` equals its `oa:exact`;
  across pages, `d2d:text` is the exacts joined with one space, in page order.
- Verbatim check: each `oa:exact` is found in the pinned text layer of its page, normalized the same way;
  labels, headings, numbers and trailing text are found on one of the element's pages.
- Coverage: elements of a transcript graph that no `jt:derivedFrom` points to.

## Transcript runs

Each transcript graph is a `prov:Entity` generated by one run. Run records live in their own graph.

```turtle
<{M}/transcript/{name}> a prov:Entity ;
    prov:wasGeneratedBy <{M}/transcript/{name}/run/{k}> .

<{M}/transcript/{name}/run/{k}> a prov:Activity ;
    prov:used <{M}> , <{B}sha256/{hex of the text layer}> ;
    d2d:textNormalization d2d:whitespaceCollapsed ;
    prov:qualifiedAssociation [ prov:agent <…> ; prov:hadRole d2d:transcriber ] ,
                              [ prov:agent <…> ; prov:hadRole d2d:checker ] .
```

The text layer is declared with its first page, so a check can split it into pages:

```turtle
<{B}sha256/{hex of the text layer}> a prov:Entity ;
    prov:wasDerivedFrom <{M}> ;
    d2d:firstPageIndex {n} .
```

A script is a `prov:SoftwareAgent` named by path and commit. Its inputs are `prov:used` by their sha256
IRIs, the same hashes as in `inputs/MANIFEST.sha256`.

## Decisions that point at transcript elements

Mapping rows (SSSOM) use a transcript element IRI as `subject_id` and carry `subject_label`. Local ids can
shift if a document is transcribed again. Before a run uses a mapping row, it checks `subject_label`
against the element's current text and stops on a mismatch. A deliberate re-transcription gets a new
producer segment version and an explicit old → new IRI map.

## Register

Which file embodies which version of which protocol, about which study, is said in a register, never in an IRI.
`register/register.trig` is generated by `machinery/ctgov_register.py` from two inputs:
- `register/assignments.tsv`, kept by hand: the decisions. One row per Expression (a combined file, e.g. protocol
  and SAP, is one Manifestation in two rows): the opaque ids it gets
  (study `s`, work `w`, expression `e`, four digits), the ClinicalTrials.gov document it is, its sha256, where and
  when it was retrieved, and who reviewed the row.
- pinned ClinicalTrials.gov records (`register/inputs/ctgov/{NCT}.json`, API v2, sha256 in
  `register/inputs/MANIFEST.sha256`; where and when each was retrieved in `register/inputs/ctgov/SOURCES.tsv`): the
  facts. The study's registered identifiers and brief title, the document's label, date and size. Nothing is read
  from the document itself.

```turtle
<{B}study/s0001> a obo:OBI_0000066 ;                       # investigation
    d2d:registeredId [ d2d:idField "nctId" ; d2d:idValue "…" ] , … .
<{B}work/w0001> a frbr:Work ; obo:IAO_0000136 <{B}study/s0001> .   # is about
<{B}expr/e0001> a frbr:Expression ; frbr:realizationOf <{B}work/w0001> ;
    dcterms:type "…" ; dcterms:date "…"^^xsd:date .        # as ClinicalTrials.gov lists the document
<{B}sha256/{hex}> a frbr:Manifestation ; frbr:embodimentOf <{B}expr/e0001> ;
    d2d:sha256 "…" ; d2d:byteSize … ; pav:retrievedFrom <…> ; pav:retrievedOn "…"^^xsd:dateTime .
```

The Study is not the Work: a study can outlive several protocols, and one master protocol can govern several
studies. USDM and M11 views bind at the Expression (`{Expression}/usdm/`, `{Expression}/m11/`). One Manifestation
per Expression is transcribed (the table has one row per Expression, and the check below fails a run that loads two).

## Checks

`machinery/d2d_iri.py` mints the IRIs above (and prints a file's sha256 IRI). `machinery/d2d_check.py` runs five
checks over transcript graphs:
- `verbatim`: IRIs follow the templates; strings are on their pages in the pinned text layer (above); each
  element's `d2d:withinSection` is the nearest section reached through its direct containers.
- `structure`: against the PDF. Table parts sit in the printed table as the transcript says: each cell in exactly
  one ruled cell; same row = same row band, same column = same column band; row, column and table order kept,
  also across a page break; a printed-empty cell is an empty ruled cell; row, column and row group labels in
  place. Exactly one placement must fit. A cell printed across columns spans them, its edges in column order. Only
  rules bound cells: a filled rectangle thicker than a rule and not black is shading and is left out (a black box,
  e.g. a redaction, is kept). A row may continue across a page break. A ruled row whose non-empty
  cells (two or more) all print the same text is read as one cell spanning them (a row group label printed in each
  column). Everything not part of a table is printed outside every table, and a section heading follows its number
  on one line; text outside tables is also matched in content-stream order, so a sub- or superscript set off its
  line does not break a string. Ruled regions nested inside a table are ignored; list-marker fonts are named on the
  command line. Captions are not checked yet (none seen so far).
- `coverage`: printed elements no rule used (no `jt:derivedFrom` points to them).
- `drift`: each SSSOM row's `subject_label` equals its element's printed name (label, else heading, else text).
- `register`: the transcripts' Manifestations are in the register; one Manifestation per Expression in a run; the
  PDF's sha256 and size match the register; at least one of the study's registered identifiers is printed on the
  pinned pages, so the register and the document agree.

## Not in v0

Figures beyond the IAO class (figure transcripts are future work); USDM and M11 views (layer 3); the
register's file format; alignment of `rulerun.py`'s run records (`jt:Firing`, `jt:derivedFrom`) with PROV-O.
