# Test: layer-1 checks on a public protocol (CDISC Pilot, LZZT), and a comparison with a published USDM build

A worked example of layer 1 (the transcript: what the document prints, checked against the source, no decisions) on
a protocol anyone can download, plus a per-element comparison with a USDM build that someone else has published.
There are no rules in this test.

The protocol is Xanomeline (LY246708) Protocol H2Q-MC-LZZT(c), "Safety and Efficacy of the Xanomeline Transdermal
Therapeutic System (TTS) in Patients with Mild to Moderate Alzheimer's Disease", the CDISC Pilot study. Every page
prints "Copyright © 2006 Eli Lilly and Company". The same file (sha256 below) is published in
data4knowledge/usdm_data (GPL-3.0 repository) and in cdisc-org/DDF-RA (MIT repository, `Documents/Examples/CDISC_Pilot/`),
each next to a USDM build of the study, and its SoA pages (53–54) are in kerfors/soa2usdm-collections `usdm_data`.
This test quotes two of its 97 pages; it does not copy the PDF.

## Register
s0005 / w0006 / e0006 in `register/register-collections.trig`, built by `machinery/collection_register.py` from the
soa2usdm-collections workbook (identifiers study_code H2Q-MC-LZZT, study_acronym LZZT; no NCT id). The file of record
is the one the collection links to (d4k usdm_data).

## Inputs (`inputs/`, sha256 in `inputs/MANIFEST.sha256`)
- `text-layer/p001.txt`, `text-layer/p007.txt`: the PDF's text layer for pages 1 and 7, from
  `pdftotext -f N -l N CDISC_Pilot_Study.pdf` (poppler 24.02.0), one file per page, each ending in a form feed.
- `downloaded/`: **not in this repository**. Download both files into `tests/lzzt-layer1/inputs/downloaded/`:
  ```
  curl -sS -o tests/lzzt-layer1/inputs/downloaded/CDISC_Pilot_Study.pdf https://raw.githubusercontent.com/data4knowledge/usdm_data/main/source_data/protocols/CDISC_Pilot/CDISC_Pilot_Study.pdf
  curl -sS -o tests/lzzt-layer1/inputs/downloaded/CDISC_Pilot_Study.json https://raw.githubusercontent.com/cdisc-org/DDF-RA/aa303cb32f5d3ceecc68a16803e26720d2c1fc26/Documents/Examples/CDISC_Pilot/CDISC_Pilot_Study.json
  ```
  - `CDISC_Pilot_Study.pdf`: the protocol, the file of record (register e0006). The URL is on d4k's `main`; the
    sha256 is the guard (d4k main was 53c8a09 on 2026-11-17).
  - `CDISC_Pilot_Study.json`: the DDF-RA USDM 4.0.0 build of the study, at DDF-RA aa303cb.

## Files
- `transcript.trig`: the d2d transcript, stage 1. Page 1 (title page): the copyright notice, the compound line, the
  protocol line and the document title. Page 7: section 2 Objectives with 2.1 and 2.2, each with its lead sentence and
  bulleted list (2 and 4 items). 17 elements, 12 anchors. The running header and footer printed on every page are not
  transcribed. The run record names the transcriber (Claude) and the checker (Kerstin Forsberg, ORCID
  0000-0002-1491-0940), who compared the 17 elements with pages 1 and 7 on 2026-11-17.
- `compare_ddfra.py`: for each DDF-RA value in scope (4 titles, 2 study identifiers, 6 objectives, 11 endpoints), how it
  relates to the transcribed pages, under the run's normalization (whitespace collapsed, nothing else): equal,
  contained, differs (difflib ratio >= 0.8, both texts shown), not printed, placeholder ("*** ... ***").
  Writes `out/ddfra_compare.tsv` and compares it with `expected_ddfra.tsv`; the run fails on any difference.

## Run
From the repository root, after the two downloads: `bash run_lzzt.sh`. It checks the manifest, then runs the
`verbatim`, `structure` and `register` checks of `machinery/d2d_check.py` and `compare_ddfra.py`.

## Result (2026-11-17)
- verbatim: ok (17 elements, 12 anchors, 6 other printed literals); structure: ok (no table regions; three section
  headings after their numbers); register: ok (H2Q-MC-LZZT and LZZT printed on both pinned pages).
- DDF-RA values: 23 | equal: 4 | contained: 2 | differs: 5 | not printed: 9 | placeholder: 3.

What the comparison shows (recorded, not resolved; the build is not ours):
- Equal: the brief title "Xanomeline (LY246708)"; objectives 2, 4 and 6.
- Contained: identifier H2Q-MC-LZZT in "Protocol H2Q-MC-LZZT(c)"; the acronym LZZT, which the transcribed elements
  print only inside the protocol line and the attachment references ("Attachment LZZT.2").
- Differs: the official and public titles (straight apostrophe in "Alzheimer's", the page prints ’); objective 1 (the
  page prints "error rate, α=.05" and "ADAS-Cog (see Attachment LZZT.2) and CIBIC+ (see Attachment LZZT.3)", the build
  "erroralpha=0.05" and "the ADAS-Cog (11) and CIBIC+"); objective 3 (the build leaves out "(see Attachment
  LZZT.4)"); objective 5 (apostrophe).
- Not printed on these pages: the second study identifier NCT12345678 (no NCT number, "NCT" followed by a digit, is printed
  anywhere in the protocol's text layer), and 8 endpoints. The protocol has no endpoints section; whether their texts are printed elsewhere
  (e.g. 3.9.1.1 Efficacy Measures) is a later stage.
- Placeholder: endpoints 9–11, "*** To be determined from protocol ***".
