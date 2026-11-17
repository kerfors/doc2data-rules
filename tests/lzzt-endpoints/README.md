# Test: LZZT stage 2a — endpoints from their printed source

The LZZT worked example (`WALKTHROUGH.md`), stage 2a. The protocol prints no endpoints next to its objectives (section 2),
but section 3.9.1.2 Efficacy Criteria (PDF page 29) names the efficacy instruments and their level:

> The ADAS-Cog (11) and the video-referenced CIBIC+ will serve as the primary efficacy instruments. Secondary efficacy
> instruments will include the DAD, the NPI-X, and the ADAS-Cog (14).

This test transcribes that section (layer 1), and builds one USDM Endpoint per named instrument, inside the objective that
prints the same instrument (layer 2, decided rows), run together with stage 1 (`tests/lzzt-usdm`), validated (layer 3).

## Files
- `transcript.trig`: d2d transcript of page 29, the whole section 3.9.1.2: heading and its 7 sentences (two printed
  paragraphs; the paragraph break is not recorded). 8 elements, 7 anchors. Transcriber Claude; checked by the
  verbatim and structure checks, no human checker (plain prose; working rule of 2026-11-17).
  `inputs/text-layer/p029.txt`: pdftotext output for page 29 (poppler 24.02.0), sha256 in `inputs/MANIFEST.sha256`.
- `el.sssom.tsv`: endpoint level by criteria sentence. el:1 sentence 2 → NCIT:C94496 "Primary Endpoint"; el:2 sentence 3
  → NCIT:C139173 "Secondary Endpoint" (codelist C188726, DDF CT 2026-09-25).
- `eo.sssom.tsv`: endpoint → objective. One row per instrument named in a criteria sentence; the object is the printed
  objective (stage-1 transcript element); `match_string` is printed on both sides (the drift check verifies it);
  `subject_mention` is the instrument as printed in the sentence, and becomes the endpoint text (`check.py` verifies it is
  printed there):

  | row | sentence | subject_mention | match_string | objective |
  |---|---|---|---|---|
  | eo:1 | 2 | ADAS-Cog (11) | ADAS-Cog | 2.1.1 |
  | eo:2 | 2 | video-referenced CIBIC+ | CIBIC+ | 2.1.1 |
  | eo:3 | 3 | NPI-X | NPI-X | 2.2.1 |
  | eo:4 | 3 | DAD | DAD | 2.2.2 |
  | eo:5 | 3 | ADAS-Cog (14) | ADAS-Cog (14) | 2.2.3 |

  Objectives 2.1.2 (safety profile) and 2.2.4 (Apo E genotype) name no efficacy instrument: no row, no endpoint.
  eo:2–5 print the same string on both sides: lexical matches (`semapv:LexicalMatching`, no reviewer), held by the
  drift check. eo:1 is a decision ("ADAS-Cog (11)" → the objective that prints only "ADAS-Cog"), and so are el:1
  and el:2 (a sentence gives the level): `semapv:ManualMappingCuration`, reviewer_id Kerstin Forsberg.
- `rules.trig`: E1 Endpoint in its Objective (text = subject_mention; name and purpose not stated: the not-stated pattern
  plus ""); E2 its level Code from the sentence's level row. Node ids from the objective's print position and the
  instrument (`Endpoint_2.1.1_ADAS-Cog%20%2811%29`).
- `check.py`: shape (SHACL with usdm-rdf, over the whole stage 1 + 2a output), ct, mention, owner (each Endpoint in exactly
  one Objective), provenance, coverage over both transcripts, counts.
- `compare_ddfra_endpoints.py`: per objective (paired by layer 1), DDF-RA's endpoints next to ours; an endpoint pair is
  made when the row's match_string occurs in the DDF-RA endpoint text. Compared with `expected_ddfra_endpoints.tsv`.

Inputs from the other LZZT tests: the stage-1 transcript, rules and rows; the PDF and the DDF-RA JSON
(`tests/lzzt-layer1/inputs/downloaded/`); the DDF CT package and the usdm-rdf files (`tests/lzzt-usdm/inputs/`).

## Run
From the repository root: `bash run_lzzt.sh` (layer 1, stage 1, then this test).

## Result (2026-11-17)
- Transcript: verbatim, structure, register ok. Rules: E1 +95, E2 +35 quads (with stage 1: 181 triples).
- shape: conforms, 0 results. ct: 12 of 12 Codes in DDF CT 2026-09-25. mention: 5 of 5 printed. owner: 5 of 5 in exactly
  one Objective. provenance: 40 output nodes, all derived. drift: ok (7 rows).
- coverage: 23 printed elements, 11 used; not used: stage 1's six, the 3.9.1.2 heading and sentences 1, 4–7 (the criteria
  sentence "Group mean changes from baseline…" and the analysis sentences: not read by any rule in this stage).
- counts: 5 Endpoints (2 Primary, 3 Secondary); no Week 24: the time point is printed in 3.1, not in 3.9.1.2.
- Negative controls (run by Claude, not part of the run): eo:5 subject_mention "ADAS-Cog (41)" → mention fails; eo:4
  match_string "ADL" → drift fails; el:2 removed → the three secondary endpoints are not built, coverage fails.
- DDF-RA vs ours: DDF-RA 11 endpoints, ours 5; paired 3 (all same level): ADAS-Cog (11) and CIBIC+ under objective 1,
  NPI-X under objective 3 (our 2.2.1). DDF-RA only: 3 safety endpoints under objective 2 (adverse events, vital signs,
  laboratory evaluations; not named in 3.9.1.2), ADAS-Cog (11) and CIBIC+ "at Weeks 8 and 16" under objective 3 (the
  behaviour objective), 3 placeholders "*** To be determined from protocol ***". Ours only: DAD (2.2.2) and ADAS-Cog (14)
  (2.2.3), both named as secondary instruments in 3.9.1.2 and printed in those objectives.
