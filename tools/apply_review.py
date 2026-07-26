# -*- coding: utf-8 -*-
"""Fold browser review marks back into solutions/chNN.md.

Prat reviews solutions in the viewer (iPad-friendly), taps ✓ ถูก / ✗ ผิด, then
exports JSON from the 📥 ผลตรวจ button. This script reads that JSON and updates
the **Checked:** line of each question in place.

    python tools/apply_review.py chem-review.json
    python tools/apply_review.py chem-review.json --dry-run

What it writes:
    v == "ok"   ->  **Checked:** yes
    v == "bad"  ->  **Checked:** ⚠️ ผิด — <his note>       (so it can't be mistaken for verified)
    note only   ->  appends the note, leaves Checked alone

It never touches **Answer:**, **Confidence:**, or the **Solution:** body — a wrong
answer still has to be rewritten by hand. This only records the verdict.
"""
import json, os, re, sys, io

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOLDIR = os.path.join(ROOT, "solutions")


def load_payload(path):
    raw = open(path, encoding="utf-8").read().strip()
    data = json.loads(raw)
    if isinstance(data, dict) and "items" in data:
        return data["items"]
    if isinstance(data, list):
        return data
    raise SystemExit("unrecognised file — expected the JSON from the 📥 ผลตรวจ button")


def verdict_line(item):
    v, note = item.get("v", ""), (item.get("note") or "").strip()
    if v == "ok":
        return "yes" + (f"  <!-- {note} -->" if note else "")
    if v == "bad":
        return "⚠️ ผิด — " + (note if note else "ยังไม่ระบุว่าผิดตรงไหน")
    return None  # note-only: leave Checked as-is


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    dry = "--dry-run" in sys.argv or "-n" in sys.argv
    if not args:
        raise SystemExit("usage: python tools/apply_review.py <chem-review.json> [--dry-run]")

    items = {it["id"]: it for it in load_payload(args[0]) if it.get("id")}
    if not items:
        raise SystemExit("no review marks in that file")

    files = sorted(f for f in os.listdir(SOLDIR) if f.endswith(".md"))
    applied, notfound = 0, set(items)

    for fn in files:
        path = os.path.join(SOLDIR, fn)
        text = open(path, encoding="utf-8").read()
        blocks = re.split(r"(?m)^(?=### Q-\d+\b)", text)
        changed = False

        for i, blk in enumerate(blocks):
            m = re.match(r"### (Q-\d+)\b", blk)
            if not m or m.group(1) not in items:
                continue
            qid = m.group(1)
            notfound.discard(qid)
            item = items[qid]
            new_val = verdict_line(item)

            note = (item.get("note") or "").strip()
            if new_val is None and note:
                if "<!-- note:" not in blk:
                    blk = blk.rstrip() + f"\n<!-- note: {note} -->\n\n"
                    blocks[i] = blk
                    changed = True
                    applied += 1
                continue
            if new_val is None:
                continue

            new_blk, n = re.subn(r"(?m)^\*\*Checked:\*\*.*$",
                                 "**Checked:** " + new_val, blk, count=1)
            if n == 0:
                print(f"  !! {qid}: no **Checked:** line found, skipped")
                continue
            if new_blk != blk:
                blocks[i] = new_blk
                changed = True
                applied += 1
                print(f"  {qid} -> {new_val}")

        if changed and not dry:
            open(path, "w", encoding="utf-8").write("".join(blocks))
            print(f"  wrote {fn}")

    print(f"\n{'[dry run] would apply' if dry else 'applied'} {applied} mark(s)")
    if notfound:
        print("not found in any solutions file:", ", ".join(sorted(notfound)))
    if applied and not dry:
        print("\nnow run:  python tools/build_viewer.py")


if __name__ == "__main__":
    main()
