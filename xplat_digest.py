"""xplat_digest.py -- cross-platform output comparator for XPLAT_PREREG.md.

Stdlib only. Three modes:

  python xplat_digest.py digest OUTDIR
      Normalize every *.txt in OUTDIR and print "<sha256>  <name>" lines.

  python xplat_digest.py compare DEVICE_FILE LEG_DIR [LEG_DIR ...]
      P2: each leg's d3.txt must equal DEVICE_FILE after normalization.
      P3: every output name must have exactly one sha256 across all legs.
      Exit 0 only if both hold; exit 1 otherwise.

  python xplat_digest.py --selftest
      Anti-vacuity: the comparator must report agreement on identical inputs
      AND a mismatch when one byte of one output is altered.

Normalization is fixed by XPLAT_PREREG.md and must not grow after results:
  1. remove "\\r"   2. drop lines starting "runtime "
  3. drop lines starting "python          :"
"""
import hashlib
import os
import sys
import tempfile

DROP_PREFIXES = ("runtime ", "python          :")


def normalize(raw: bytes) -> bytes:
    text = raw.replace(b"\r", b"").decode("utf-8")
    kept = [ln for ln in text.split("\n") if not ln.startswith(DROP_PREFIXES)]
    return "\n".join(kept).encode("utf-8")


def sha(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(normalize(f.read())).hexdigest()


def outputs(leg_dir: str) -> dict:
    return {n: sha(os.path.join(leg_dir, n))
            for n in sorted(os.listdir(leg_dir)) if n.endswith(".txt")}


def compare(device_file: str, leg_dirs: list) -> bool:
    ok = True
    device = sha(device_file)
    legs = {os.path.basename(os.path.normpath(d)): outputs(d) for d in leg_dirs}
    if not legs:
        print("FAIL no legs supplied")
        return False

    print("P2 device agreement (d3.txt vs %s)" % os.path.basename(device_file))
    for leg, outs in legs.items():
        got = outs.get("d3.txt")
        verdict = "MATCH" if got == device else ("MISSING" if got is None else "DIFFER")
        ok &= verdict == "MATCH"
        print("  %-28s %s" % (leg, verdict))

    print("P3 cross-leg agreement")
    names = sorted({n for outs in legs.values() for n in outs})
    for name in names:
        hashes = {leg: outs.get(name) for leg, outs in legs.items()}
        distinct = {h for h in hashes.values()}
        agree = len(distinct) == 1 and None not in distinct
        ok &= agree
        print("  %-12s %s %s" % (name, "AGREE " if agree else "SPLIT ",
                                 next(iter(distinct))[:12] if agree else ""))
        if not agree:
            for leg, h in hashes.items():
                print("      %-26s %s" % (leg, h[:12] if h else "MISSING"))

    print("VERDICT", "P2+P3 HOLD" if ok else "P2/P3 VIOLATED")
    return ok


def selftest() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        dev = os.path.join(tmp, "device.txt")
        body = b"header\npython          : 3.14 platform=android\nk* 4\nruntime 9.9s\n"
        with open(dev, "wb") as f:
            f.write(body)
        legs = []
        for i, variant in enumerate([
            body,
            body.replace(b"\n", b"\r\n").replace(b"android", b"win32"),
            body.replace(b"9.9s", b"123.4s"),
        ]):
            d = os.path.join(tmp, "leg%d" % i)
            os.mkdir(d)
            for name in ("d3.txt", "arm.txt"):
                with open(os.path.join(d, name), "wb") as f:
                    f.write(variant)
            legs.append(d)
        devnull = open(os.devnull, "w")
        real_stdout, sys.stdout = sys.stdout, devnull
        try:
            agrees = compare(dev, legs)
            with open(os.path.join(legs[2], "arm.txt"), "wb") as f:
                f.write(body.replace(b"k* 4", b"k* 5"))
            catches_split = not compare(dev, legs)
            with open(os.path.join(legs[1], "d3.txt"), "wb") as f:
                f.write(body.replace(b"k* 4", b"k* 5"))
            catches_device = not compare(dev, legs)
        finally:
            sys.stdout = real_stdout
            devnull.close()
    checks = [("identical-after-normalization inputs agree", agrees),
              ("one altered byte in arm.txt is reported", catches_split),
              ("one altered byte in d3.txt vs device is reported", catches_device)]
    for label, passed in checks:
        print("  %s  %s" % ("PASS" if passed else "FAIL", label))
    ok = all(p for _, p in checks)
    print("SELFTEST:", "PASS (the comparator can fail)" if ok else "FAIL")
    return ok


def main(argv: list) -> int:
    if argv[:1] == ["--selftest"]:
        return 0 if selftest() else 1
    if len(argv) >= 2 and argv[0] == "digest":
        for name, h in outputs(argv[1]).items():
            print("%s  %s" % (h, name))
        return 0
    if len(argv) >= 3 and argv[0] == "compare":
        return 0 if compare(argv[1], argv[2:]) else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
