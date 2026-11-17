"""d2d_iri — mint the IRIs of TRANSCRIPT-VOCABULARY.md, and check that existing IRIs follow the templates.

Templates ({B} = base, {M} = Manifestation IRI):
  file / Manifestation   {B}sha256/{hex}        hex = SHA-256 of the file's bytes, 64 lowercase characters
  page                   {M}/page/{n}           n = physical page, from 1
  transcript element     {M}/{producer}/{localId}
  anchor                 {element}/anchor/{k}   k from 1
  transcript graph       {M}/transcript/{name}
  transcript run         {M}/transcript/{name}/run/{k}
  Work / Expression      {B}work/w{nnnn} / {B}expr/e{nnnn}
  Study                  {B}study/s{nnnn}

{B} is urn:jt: for now (later https://w3id.org/people/kerfors/doc2data/).
Usage as a script: python3 d2d_iri.py [--base B] FILE ...   prints "hex  IRI  path" per file.
"""
import argparse
import hashlib
import re

BASE = "urn:jt:"
SEGMENT = re.compile(r"[A-Za-z0-9._-]+")
HEX64 = re.compile(r"[0-9a-f]{64}")


def segment(s):
    if not SEGMENT.fullmatch(s):
        raise ValueError(f"not a valid IRI segment (allowed: A-Z a-z 0-9 . _ -): {s!r}")
    return s


def positive(n):
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError(f"not a positive integer: {n!r}")
    return n


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_iri(hexdigest, base=BASE):
    if not HEX64.fullmatch(hexdigest):
        raise ValueError(f"not a lowercase 64-character sha256: {hexdigest!r}")
    return f"{base}sha256/{hexdigest}"


def page_iri(m, n):
    return f"{m}/page/{positive(n)}"


def element_iri(m, producer, local_id):
    return f"{m}/{segment(producer)}/{segment(local_id)}"


def anchor_iri(element, k):
    return f"{element}/anchor/{positive(k)}"


def transcript_iri(m, name):
    return f"{m}/transcript/{segment(name)}"


def run_iri(m, name, k):
    return f"{transcript_iri(m, name)}/run/{positive(k)}"


def work_iri(n, base=BASE):
    return f"{base}work/w{positive(n):04d}"


def expression_iri(n, base=BASE):
    return f"{base}expr/e{positive(n):04d}"


def study_iri(n, base=BASE):
    return f"{base}study/s{positive(n):04d}"


def register_number(rid, letter):
    """'w0001' -> 1 for letter 'w'; fails on anything but the letter and four or more digits."""
    if not re.fullmatch(letter + r"[0-9]{4,}", rid):
        raise ValueError(f"not a register id {letter}nnnn: {rid!r}")
    return int(rid[1:])


def manifestation_of(iri, base=BASE):
    """The Manifestation IRI that an IRI minted under {M} starts with."""
    m = re.match(re.escape(base) + r"sha256/[0-9a-f]{64}", iri)
    if not m:
        raise ValueError(f"not under a {base}sha256/ Manifestation: {iri}")
    return m.group(0)


def split_element(iri, base=BASE):
    """{M}/{producer}/{localId} -> (M, producer, localId); fails on anything else."""
    m = manifestation_of(iri, base)
    rest = iri[len(m):].split("/")
    if len(rest) != 3 or rest[0] != "" or rest[1] in ("page", "transcript"):
        raise ValueError(f"not a transcript element IRI {{M}}/{{producer}}/{{localId}}: {iri}")
    return m, segment(rest[1]), segment(rest[2])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default=BASE)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    for f in a.files:
        h = sha256_file(f)
        print(f"{h}  {file_iri(h, a.base)}  {f}")


if __name__ == "__main__":
    main()
