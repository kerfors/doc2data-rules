#!/usr/bin/env bash
# The LZZT worked example (CDISC Pilot protocol, register e0006), WALKTHROUGH.md. tests/lzzt-layer1: layer-1 checks
# and a comparison with the DDF-RA USDM build; tests/lzzt-usdm: rules + mapping rows -> USDM, its checks, and the
# comparison with the DDF-RA build. Needs each test's inputs/downloaded/ (protocol PDF, DDF-RA JSON, two NCI EVS DDF
# CT packages), not in this repository; how to get them: the two test READMEs, Inputs. The manifest checks stop the
# run if a file is missing or differs. Run from the folder this file is in.
set -euo pipefail
C="$(pwd)/machinery/d2d_check.py"
R="$(pwd)/register/register-collections.trig"
M="$(pwd)/machinery"
(cd tests/lzzt-layer1 && (cd inputs && shasum -a 256 -c MANIFEST.sha256 > /dev/null) \
   && python3 "$C" verbatim --transcript transcript.trig --text-layer inputs/text-layer/p001.txt inputs/text-layer/p007.txt \
   && python3 "$C" structure --transcript transcript.trig --pdf inputs/downloaded/CDISC_Pilot_Study.pdf --marker-fonts SymbolMT \
   && python3 "$C" register --transcript transcript.trig --register "$R" --pdf inputs/downloaded/CDISC_Pilot_Study.pdf \
        --text-layer inputs/text-layer/p001.txt inputs/text-layer/p007.txt \
   && python3 compare_ddfra.py)
(cd tests/lzzt-usdm && (cd inputs && shasum -a 256 -c MANIFEST.sha256 > /dev/null) && mkdir -p out \
   && python3 "$M/sssom_rdf.py" lv.sssom.tsv out/lv.trig urn:jt:g:lzzt-levelmap \
   && python3 "$M/sssom_rdf.py" ti.sssom.tsv out/ti.trig urn:jt:g:lzzt-titlemap \
   && python3 "$M/rulerun.py" --rules rules.trig --facts ../lzzt-layer1/transcript.trig out/lv.trig out/ti.trig \
        --out out --output usdm.ttl --firing-ns urn:jt:firing:lzzt: \
   && python3 check.py \
   && python3 "$C" drift --transcript ../lzzt-layer1/transcript.trig --sssom lv.sssom.tsv ti.sssom.tsv \
   && python3 compare_ddfra_usdm.py)
