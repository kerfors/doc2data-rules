# doc2data-rules — document-to-data as reviewable rules

Started 2026-11-13 after Connected Data London
2026, from Doug Beeson's talk "SPARQL Patterns for Connected Data" (Semantic Arts, Wed 11 Nov). Status as of
2026-11-17.

## The idea
Beeson described representing the shape of a knowledge graph as pure RDF — a pattern language expressed as
an OWL ontology — and using those patterns to guide AI parsers turning unstructured documents (developed
for clinical trial protocol PDFs) into fully connected, ontology-conforming triples. His public repo
[Jayhawk](https://github.com/turingtest37/Jayhawk) shows the mechanics: a rule is two RDF graphs, L (what must be present)
and R (what becomes true), compiled to SPARQL Update; each run lands in its own graph and can be undone.
His pattern vocabulary (`gistp:`) is not published.

What this folder tests: the same idea applied to my own document-to-data work, as three layers that stay
separate:

1. **Transcript** — what the document prints, checked against the source; no decisions.
2. **Rules and mapping data** — every interpretation is a named L/R rule; correspondences (crosswalks,
   alignments, code lists) are data the rules join to, never rule content.
3. **Output** — USDM (validated with usdm-rdf) or design-relationship data, with provenance and run records
   in separate graphs.

## Results
| Test | What it rebuilds | Rules | Result |
|---|---|---|---|
| `tests/cpmp-join-kind` | CPMP SoA join: how master and ISA SoAs relate, per cell (early-clinical-design-research `cpmp-soa-join`) | 22 | **2777/2777** rows identical to the notebook's `layered_grid.csv` |
| `tests/cpmp-q6` | CPMP Q6: which master defaults an ISA takes, overrides or is silent on (`01_build_modules.py`) | 6 | **48/48** rows identical to the Python build |
| `tests/lzzt-layer1` | Layer 1 on a public protocol: the d2d transcript of the CDISC Pilot protocol (LZZT) pages 1 and 7, checked against the PDF, and compared per value with the DDF-RA USDM build | 0 | verbatim, structure and register checks **ok**; 23 DDF-RA values: 4 equal, 2 contained, 5 differ, 9 not printed on these pages, 3 placeholders (run with `run_lzzt.sh`, see below) |
| `tests/remapcap-q7` | REMAP-CAP Q7: DSA statements on the Core, what they resolve to, and which are affected by Core 4.0 → 4.1 (remapcap-design-modules scripts 07, 08) | 15 | **139/139** readings and **54/54** affected statements identical; "changed in 4.1" comes from comparing two runs, not from a rule (run with `run_remapcap.sh`, see below) |

The two CPMP tests together are a rule-based path from the SoA documents to the design-module allocations
that reproduces the existing Python results exactly. `run_all.sh` runs them and rebuilds the register
(`register/`), comparing it with the committed `register.trig` and `register-collections.trig`. The REMAP-CAP
test needs the section text of the 12 REMAP-CAP documents, which is not redistributed (as in
early-clinical-design-research); `run_remapcap.sh` runs it once that file is rebuilt (`tests/remapcap-q7/README.md`,
Inputs).

## What runs here, and what does not
- **Runs here:** the rule compiler and runner (`rulerun.py`) with mapping data as `jt:` graphs and as an SSSOM
  set (`sssom_rdf.py`: the CPMP crosswalk), on the two CPMP tests; the register rebuild.
- **Code here, evidence outside:** the d2d transcript vocabulary and its checks (`d2d_iri.py`, `d2d_check.py`),
  the drift check of SSSOM rows against a transcript, USDM output validated with usdm-rdf, and the coverage query.
  They are used on ClinicalTrials.gov protocol documents in tests kept outside this repository, because those
  tests contain protocol text. There is no public worked example for them yet.

## What the tests showed
The first three points can be seen in the tests here. The next three come from the protocol tests outside this
repository (code here, see above); of the sixth, the CPMP crosswalk shows the proposed state here. The register in
the last point is here; the transcripts minted under it are not.
- **Interpretation becomes visible.** Decisions that sit inside build scripts or prompts become short
  named rules: "an endpoint takes its objective's level", "each sub-bullet is its own endpoint", "the
  override wins", "an ISA takes a master default unless it overrides it". "The override wins" is a negative
  condition, not branch order in code.
- **Mapping data stays data.** The CPMP crosswalk and the REMAP-CAP transition reading are separate graphs,
  reviewed on their own. SSSOM says what corresponds; rules say what to build from it.
- **Unknown is recorded, not guessed.** A rule without its input does not fire.
- **Leftovers are listed.** A coverage query lists transcript elements no rule consumed — the worklist and
  the model-gap list in one.
- **Transcripts are checked against the page.** `d2d_check.py`: verbatim (every printed string is on its page in
  the PDF text layer), structure (table cells placed from the page's ruling lines), register (a registered
  identifier is printed on the pinned pages), drift (each mapping row still matches the text it was decided on),
  coverage.
- **Mapping data carries its review state.** Correspondences are SSSOM: proposed (no reviewer), accepted
  (reviewer), kept apart (reviewer and `Not`). `sssom_rdf.py` turns the TSV into a named graph the rules read.
- **Documents have identity.** The register gives each study, protocol, version and file its own IRI (the file
  by sha256), from pinned ClinicalTrials.gov records; transcript elements are minted under the file's IRI.

## What came back from usdm-rdf (2026-11-14, b26af25)
Landed: a minimal instance from CDISC's pilot; the `sh:in` / `xsd:string` known gap (pySHACL #286, rdflib
#2123); "Instance data around the shapes" (USDM in its own named graph; node IRIs = caller-minted base +
USDM id; plain string literals; extension URLs owned by whoever defines them). Waiting for USDM 4.1: one
owner per composed object (sharing an IntercurrentEvent will be a Violation), CT
as data (rules can then join by C-code instead of a hand-held level map), code + decode check.

## Folder
```
machinery/rulerun.py    the compiler and runner (shared by all tests)
machinery/d2d_iri.py    IRIs of the d2d transcript vocabulary (TRANSCRIPT-VOCABULARY.md)
machinery/d2d_check.py  verbatim, structure, coverage, drift and register checks over d2d transcripts
machinery/ctgov_register.py  the register from assignments.tsv and pinned ClinicalTrials.gov records
machinery/collection_register.py  register entries from assignments-collections.tsv and pinned soa2usdm
                        collection workbooks (protocols without a ClinicalTrials.gov record)
machinery/sssom_rdf.py  SSSOM TSV mapping sets to a named graph for the rules
register/               register.trig and register-collections.trig (generated), assignments.tsv and
                        assignments-collections.tsv (hand-kept), inputs/ (pinned CT.gov records, collection workbooks)
VOCABULARY.md           the jt: rule vocabulary
vocab/d2d.ttl, TRANSCRIPT-VOCABULARY.md  the d2d transcript vocabulary and its description
requirements.txt        rdflib, pyoxigraph, pyshacl, pandas, openpyxl, pyyaml, pdfplumber
run_all.sh              rebuild and check the register and the two CPMP tests
run_remapcap.sh         the REMAP-CAP test (needs its not-redistributed section text)
run_lzzt.sh             the LZZT layer-1 test (needs the protocol PDF and the DDF-RA JSON, downloaded)
LICENSE                 MIT
tests/<test>/           README, facts script (build_facts*.py), rules, check/compare, inputs/ (pinned, sha256), out/
```
Run: `pip install -r requirements.txt` then `./run_all.sh`. `./run_remapcap.sh` needs
`tests/remapcap-q7/inputs/not-redistributed/sections.csv` first. `bash run_lzzt.sh` needs the two downloads in
`tests/lzzt-layer1/README.md` (Inputs) first.

Identifiers: all IRIs are `urn:jt:` for now. They are provisional and will move to
`https://w3id.org/people/kerfors/doc2data/` later (see TRANSCRIPT-VOCABULARY.md, IRIs); do not depend on them yet.

## Limits
- Prose patterns are sponsor- and author-specific; a rule that does not match simply does not fire.
- Cross-document identity (which phrase means which endpoint) still needs human review.
- The rules populate a target (USDM, or design-relationship data in the tests here); they do not supply an
  ontology behind the content. A reference ontology can enter as mapping data that rows point to, as NCIt codes
  do today. This repo holds the machinery and public-data tests.
- Not tuned: the join test takes about 45 s.

## Where to go next
1. **Q7 version binding** (REMAP-CAP Core 4.0 → 4.1): done 2026-11-14, `tests/remapcap-q7` — re-run on
   the new Core and compare provenance; 54 affected statements, as the Python build.
2. **Status labels from mapping status**: done 2026-11-14, `tests/cpmp-join-kind` rules ST1-ST3 — 469 cells
   "rule-derived from analyst readings" while their crosswalk entries are proposed.
3. **Align with usdm-rdf conventions**: node IRIs = base + USDM id, done in the protocol tests outside this
   repository; join to CT as data when USDM 4.1 lands.
4. **A public worked example** for the transcript checks and the drift check of SSSOM rows: transcript checks
   started 2026-11-17, `tests/lzzt-layer1` (CDISC Pilot protocol, published by d4k and CDISC DDF-RA); the drift
   check needs mapping rows and is not there yet.
5. **Resolvable IRIs**: from `urn:jt:` to `https://w3id.org/people/kerfors/doc2data/`, with its w3id entry.

## Licence
MIT, see `LICENSE`.

## Credit
Kudos to Doug Beeson (Semantic Arts). The mechanics are his: rules as pairs of RDF graphs (L and R) compiled
to SPARQL Update, one graph per run, undone by dropping it. He presented them in "SPARQL Patterns for
Connected Data" at Connected Data London 2026 and shows them in his repo
[Jayhawk](https://github.com/turingtest37/Jayhawk). This repo is an independent re-implementation in Python
with its own minimal vocabulary (`jt:`), since his pattern vocabulary is not published. What it adds: each rule
is a named unit, reviewed on its own, and the mapping data the rules join to is kept outside them. Any errors
here are mine.

## Provenance of this folder
Built in Claude sessions from 2026-11-13. The three tests above were re-run with `machinery/rulerun.py` on
2026-11-14 before copying here; `run_all.sh` re-runs the two CPMP tests and the register,
`run_remapcap.sh` the REMAP-CAP test.
