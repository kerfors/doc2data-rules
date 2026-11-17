# The jt: rule vocabulary

A small vocabulary for writing document-to-data rules as RDF, in the style of Doug Beeson's Jayhawk
(github.com/turingtest37/Jayhawk): a rule is a match graph (L) and a construct graph (R). Jayhawk's own
pattern vocabularies (`gistp:`, `jhp:`) are not published, so this one is minimal and local.

Namespaces: `jt:` = `<urn:jt:rule-vocab:>`, variables `v:` = `<urn:jt:var:>`.

## A rule
```turtle
<urn:jt:g:rules> {
  :R2 a jt:Rule ; jt:seq 2 ;
      rdfs:label "Plain endpoint bullet to Endpoint" ;
      jt:match :R2_L ; jt:construct :R2_R ; jt:negative :R2_hasSubBullets ;
      jt:bind [ jt:seq 1 ; jt:var "ename" ; jt:expr "CONCAT('Endpoint ', ?bid)" ] ;
      jt:mint [ jt:var v:E ; jt:template "urn:...:Endpoint_{bid}" ] .
}
<urn:...:R2_L> { v:B a tr:Bullet ; tr:id "?bid"^^jt:var ; tr:text "?btext"^^jt:var . ... }
<urn:...:R2_R> { v:E a usdm:Endpoint ; usdm:SyntaxTemplate-text "?btext"^^jt:var ; jt:derivedFrom v:B . }
```

| Term | Meaning | Compiles to |
|---|---|---|
| `jt:Rule`, `jt:seq` | a rule and its run order (all rule files sorted together) | one SPARQL Update per rule |
| `jt:match` | graph name of the L pattern | `WHERE`, each triple in `GRAPH ?g` |
| `jt:construct` | graph name of the R pattern | `INSERT` into the rule's firing graph |
| `jt:negative` (repeatable) | graph name of a pattern that must not match | `FILTER NOT EXISTS { … }` |
| `jt:filter` (repeatable) | SPARQL boolean expression, spliced as is | `FILTER( … )` |
| `jt:bind` | `[ jt:seq n ; jt:var "x" ; jt:expr "…" ]`, in `jt:seq` order | `BIND( … AS ?x)` |
| `jt:mint` | `[ jt:var v:X ; jt:template "urn:…{slot}…" ]`, slots are literal variables | `BIND(IRI(CONCAT(…, ENCODE_FOR_URI(STR(?slot)), …)) AS ?X)` |
| `v:X` | variable in an IRI position | `?X` |
| `"?x"^^jt:var` | variable in a literal position | `?x` |
| `jt:derivedFrom` | provenance link in R | written to the provenance graph only, never to the output |

Runs: each rule writes into `<firing-ns><rule>`; derivation links go to `urn:jt:g:prov`; a record per rule
(time, quads added) goes to `urn:jt:g:firings`. Undo a rule = drop its firing graph.

Data graphs: any graph in a rule file named `urn:jt:g:*` (except `urn:jt:g:rules`) is loaded as data —
mapping data the rules join to (a level map, an alignment). Mapping data is never rule content.

Mapping data in SSSOM: TSV for review, turned by `machinery/sssom_rdf.py` into `owl:Axiom` form in a named
graph. One extension slot: `object_codelist` = `jt:objectCodelist`, declared in each set's
`extension_definitions`: the CDISC code list the object concept is taken from (held in the mapping set until
USDM 4.1 brings CT as data).

## Conventions used by the tests
- Facts (transcripts) live in their own graph and carry no decisions.
- A mandatory target value the source does not state is written as the not-stated pattern: an
  ExtensionAttribute with url `https://kerfors.github.io/soa2usdm/not-stated-in-protocol` naming the
  attribute — never a guessed value.
- Output string literals are plain, not `^^xsd:string` (usdm-rdf instance convention).
- Validate only the output graph; provenance and run records stay in other graphs (usdm-rdf
  `docs/shacl-design.md`, "Instance data around the shapes").
