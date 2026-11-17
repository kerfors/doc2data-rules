#!/usr/bin/env bash
# tests/remapcap-q7. Needs inputs/not-redistributed/sections.csv, which is not in this repository (section text of
# the 12 REMAP-CAP documents); how to rebuild it: tests/remapcap-q7/README.md, Inputs. The manifest check below
# stops the run if it is missing or differs. Run from the folder this file is in.
set -euo pipefail
M="$(pwd)/machinery/rulerun.py"
(cd tests/remapcap-q7 && (cd inputs && shasum -a 256 -c MANIFEST.sha256 > /dev/null) \
   && python3 build_facts.py \
   && python3 "$M" --rules rules_q7.trig mapping.trig transition.trig --facts facts.trig --out out/core40 --output q7_readings.ttl --firing-ns urn:q7:firing:core40: \
   && python3 "$M" --rules rules_q7.trig mapping.trig transition.trig --facts facts.trig facts_core41.trig --out out/core41 --output q7_readings.ttl --firing-ns urn:q7:firing:core41: \
   && python3 check.py)
