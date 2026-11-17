#!/usr/bin/env bash
# tests/lzzt-layer1: layer-1 checks on the CDISC Pilot protocol (LZZT, register e0006) and a comparison with the
# DDF-RA USDM build. Needs inputs/downloaded/ (the protocol PDF and the DDF-RA JSON), which is not in this repository;
# how to get both: tests/lzzt-layer1/README.md, Inputs. The manifest check below stops the run if a file is missing
# or differs. Run from the folder this file is in.
set -euo pipefail
C="$(pwd)/machinery/d2d_check.py"
R="$(pwd)/register/register-collections.trig"
(cd tests/lzzt-layer1 && (cd inputs && shasum -a 256 -c MANIFEST.sha256 > /dev/null) \
   && python3 "$C" verbatim --transcript transcript.trig --text-layer inputs/text-layer/p001.txt inputs/text-layer/p007.txt \
   && python3 "$C" structure --transcript transcript.trig --pdf inputs/downloaded/CDISC_Pilot_Study.pdf --marker-fonts SymbolMT \
   && python3 "$C" register --transcript transcript.trig --register "$R" --pdf inputs/downloaded/CDISC_Pilot_Study.pdf \
        --text-layer inputs/text-layer/p001.txt inputs/text-layer/p007.txt \
   && python3 compare_ddfra.py)
