# -*- coding: utf-8 -*-
"""Difficulty re-grade helper (2026-09-24 sweep).

  python tools/diff_sweep.py dump START COUNT   -> compact view of questions (by bank order) for grading
  python tools/diff_sweep.py apply              -> write grades from tools/diff_grades.txt into question-bank.md
  python tools/diff_sweep.py stats              -> distribution before/after

diff_grades.txt: one "Q-NNNN easy|medium|hard" per line (later lines win). The bank stores difficulty
in TWO places per block -- the trailing "· hard" on the ### header and #diff/hard in **Tags:** -- and
apply rewrites both, leaving every other byte untouched.
"""
import re, sys, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(ROOT, "question-bank.md")
GRADES = os.path.join(ROOT, "tools", "diff_grades.txt")
LEVELS = ("easy", "medium", "hard")

def blocks(text):
    parts = re.split(r"(?m)^(### Q-\d+\b.*)$", text)
    out = []
    for i in range(1, len(parts), 2):
        qid = re.match(r"### (Q-\d+)", parts[i]).group(1)
        out.append((qid, parts[i], parts[i + 1]))
    return parts[0], out

def body_of(rest):
    lines = rest.splitlines()
    keep = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("**Tags:**"): continue
        if s.startswith(("**Answer:**", "**Source:**", "**Also appears:**")): break
        if s.startswith("**Note:**"): keep.append("[NOTE] " + s[9:].strip()[:120]); continue
        if s.startswith("**Figure:**"): keep.append("[FIG]"); continue
        if s: keep.append(s)
    return " / ".join(keep)

def dump(start, count):
    _, bl = blocks(open(BANK, encoding="utf-8").read())
    for qid, head, rest in bl[start:start + count]:
        tags = re.search(r"\*\*Tags:\*\*(.*)", rest).group(1)
        d = (re.search(r"#diff/(\w+)", tags) or [0, "?"])[1]
        ex = (re.search(r"#exam/(\w+)", tags) or [0, "?"])[1]
        ch = (re.search(r"#ch/(\d+)", tags) or re.search(r"#bio/([\d.]+)", tags) or re.search(r"#app/(\w+)", tags) or [0, "?"])[1]
        b = body_of(rest)
        if len(b) > 400: b = b[:400] + "…"
        print(f"{qid} [{d}] {ex} ch{ch} | {b}")
    print(f"-- shown {start}..{start + count - 1} of {len(bl)}")

def load_grades():
    g = {}
    if os.path.exists(GRADES):
        for ln in open(GRADES, encoding="utf-8"):
            m = re.match(r"\s*(Q-\d+)\s+(easy|medium|hard)\b", ln)
            if m: g[m.group(1)] = m.group(2)
    return g

def apply():
    text = open(BANK, encoding="utf-8").read()
    pre, bl = blocks(text)
    g = load_grades(); changed = 0; out = [pre]
    for qid, head, rest in bl:
        if qid in g:
            new = g[qid]
            h2 = re.sub(r"· (easy|medium|hard)\s*$", "· " + new, head)
            r2 = re.sub(r"#diff/(easy|medium|hard)", "#diff/" + new, rest, count=1)
            if (h2, r2) != (head, rest): changed += 1
            head, rest = h2, r2
        out.append(head); out.append(rest)
    new_text = "".join(out)
    assert len(bl) == len(blocks(new_text)[1])
    open(BANK, "w", encoding="utf-8").write(new_text)
    print(f"graded {len(g)} · blocks changed {changed}")

def stats():
    _, bl = blocks(open(BANK, encoding="utf-8").read())
    g = load_grades(); before = collections.Counter(); after = collections.Counter(); moves = collections.Counter()
    for qid, head, rest in bl:
        d = (re.search(r"#diff/(\w+)", rest) or [0, "?"])[1]
        before[d] += 1; n = g.get(qid, d); after[n] += 1
        if n != d: moves[f"{d}->{n}"] += 1
    print("current:", dict(before)); print("with grades:", dict(after)); print("moves:", dict(moves)); print("graded:", len(g), "/", len(bl))

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "dump": dump(int(sys.argv[2]), int(sys.argv[3]))
    elif cmd == "apply": apply()
    elif cmd == "stats": stats()
