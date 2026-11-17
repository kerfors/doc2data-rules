#!/usr/bin/env bash
# Rebuild facts, run the rules and check every test whose inputs are in this repository. Run from the folder
# this file is in. tests/remapcap-q7 needs section text that is not redistributed: see run_remapcap.sh.
set -euo pipefail
M="$(pwd)/machinery/rulerun.py"
(cd register/inputs && shasum -a 256 -c MANIFEST.sha256 > /dev/null)
mkdir -p register/out
python3 machinery/ctgov_register.py register/assignments.tsv register/inputs/ctgov register/out/register.trig
cmp register/out/register.trig register/register.trig
(cd tests/cpmp-join-kind && (cd inputs && shasum -a 256 -c MANIFEST.sha256 > /dev/null) \
   && mkdir -p out && python3 crosswalk_sssom.py out/crosswalk.sssom.tsv && cmp out/crosswalk.sssom.tsv crosswalk.sssom.tsv \
   && python3 ../../machinery/sssom_rdf.py crosswalk.sssom.tsv out/crosswalk.trig urn:k:g:crosswalk \
   && python3 build_facts_kind.py \
   && python3 "$M" --rules rules_kind.trig --facts facts.trig out/crosswalk.trig --out out --output kind_cells.ttl --firing-ns urn:k:firing: \
   && python3 compare_kind.py)
(cd tests/cpmp-q6 && (cd inputs && shasum -a 256 -c MANIFEST.sha256 > /dev/null) \
   && python3 build_facts.py \
   && python3 "$M" --rules rules_q6.trig --facts facts.trig --out out --output q6_allocations.ttl --firing-ns urn:q6:firing: \
   && python3 compare.py)
