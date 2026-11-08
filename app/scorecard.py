"""Score the four retrieval methods on the sample library.

Retrieval metrics look at the top 10 chunks. Answer metrics use the app's normal top 5 plus the model's answer.
A chunk is "on page" when it is on an expected page of an expected document (see samples.py); "on doc" only
needs the right document, which separates finding the document from finding the page.

CLI: python scorecard.py  ->  writes scorecard_results.json and SCORECARD.md
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import app
import samples
from app import MODES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(HERE, "scorecard_results.json")
OUT_MD = os.path.join(HERE, "SCORECARD.md")


def doc_ok(sample, d):
    return any(sub in d["doc"] for sub in sample["docs"])


def evaluate(sample, mode):
    t0 = time.perf_counter()
    row = {"id": sample["id"], "category": sample["category"], "mode": mode}
    if sample["category"] == "none":
        res = app.answer(sample["question"], mode=mode, top=5)
        row.update(refused=res["refused"], latency=time.perf_counter() - t0)
        return row
    docs = app.retrieve(sample["question"], top=10, mode=mode)
    row["rank_page"] = next((i for i, d in enumerate(docs, 1) if samples.source_ok(sample, d)), None)
    row["rank_doc"] = next((i for i, d in enumerate(docs, 1) if doc_ok(sample, d)), None)
    res = app.answer(sample["question"], mode=mode, top=5)
    c = samples.check(sample, res)
    row.update(ans_key=c["key_points"], ans_cited=c["cited_source"], ans_pass=c["passed"], refused=res["refused"],
               latency=time.perf_counter() - t0)
    return row


def run(progress=None):
    tasks = [(s, m) for s in samples.load() for m in MODES]
    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=3) as pool:
        for r in pool.map(lambda t: evaluate(*t), tasks):
            rows.append(r)
            done += 1
            if progress:
                progress(done / len(tasks))
    out = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "rows": rows}
    json.dump(out, open(OUT_JSON, "w"), indent=1)
    return out


def _pct(x, n):
    return f"{100 * x / n:.0f}%" if n else "-"


def aggregate(rows):
    """Per-method metrics plus per-category breakdown."""
    summary, by_cat = {}, {}
    for m in MODES:
        ans = [r for r in rows if r["mode"] == m and r["category"] != "none"]
        neg = [r for r in rows if r["mode"] == m and r["category"] == "none"]
        n = len(ans)
        rp = [r["rank_page"] for r in ans]
        summary[m] = {
            "n": n,
            "Hit@1": sum(1 for x in rp if x == 1) / n,
            "Hit@3": sum(1 for x in rp if x and x <= 3) / n,
            "Hit@5": sum(1 for x in rp if x and x <= 5) / n,
            "Hit@10": sum(1 for x in rp if x) / n,
            "MRR": sum(1 / x for x in rp if x) / n,
            "Right doc @1": sum(1 for r in ans if r["rank_doc"] == 1) / n,
            "Key facts in answer": sum(r["ans_key"] for r in ans) / n,
            "Cited expected page": sum(r["ans_cited"] for r in ans) / n,
            "Answer pass": sum(r["ans_pass"] for r in ans) / n,
            "Refused out-of-scope": sum(r["refused"] for r in neg) / max(1, len(neg)),
            "Avg latency (s)": sum(r["latency"] for r in ans + neg) / max(1, len(ans + neg)),
        }
        for cat in sorted({r["category"] for r in ans}):
            c = [r for r in ans if r["category"] == cat]
            by_cat.setdefault(cat, {})[m] = {
                "n": len(c),
                "Hit@1": sum(1 for r in c if r["rank_page"] == 1) / len(c),
                "Answer pass": sum(r["ans_pass"] for r in c) / len(c),
            }
    return summary, by_cat


def write_markdown(out):
    rows = out["rows"]
    summary, by_cat = aggregate(rows)
    n = summary[MODES[0]]["n"]
    L = [
        "# Lab 1 retrieval scorecard",
        "",
        f"Generated {out['generated']} from the sample library: **{n} answerable questions** and 2 out-of-scope questions, "
        "each run through all four methods.",
        "",
        "**Caution:** with only %d questions, one question is worth about %.0f points. Treat gaps of 1-2 questions as noise." % (n, 100 / n),
        "",
        "## Retrieval (top 10 chunks, page level)",
        "",
        "| Method | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR | Right doc @1 |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in MODES:
        s = summary[m]
        L.append(f"| {m} | {_pct(s['Hit@1'], 1)} | {_pct(s['Hit@3'], 1)} | {_pct(s['Hit@5'], 1)} | {_pct(s['Hit@10'], 1)} | "
                 f"{s['MRR']:.2f} | {_pct(s['Right doc @1'], 1)} |")
    L += ["", "## Answers (top 5 sent to the model)", "",
          "| Method | Key facts | Cited expected page | Answer pass | Refused out-of-scope | Avg latency |",
          "|---|---|---|---|---|---|"]
    for m in MODES:
        s = summary[m]
        L.append(f"| {m} | {_pct(s['Key facts in answer'], 1)} | {_pct(s['Cited expected page'], 1)} | {_pct(s['Answer pass'], 1)} | "
                 f"{_pct(s['Refused out-of-scope'], 1)} | {s['Avg latency (s)']:.1f}s |")
    L += ["", "## By question type (Hit@1 / Answer pass)", "", "| Type (n) | " + " | ".join(MODES) + " |",
          "|---|" + "---|" * len(MODES)]
    for cat, d in by_cat.items():
        L.append(f"| {cat} ({d[MODES[0]]['n']}) | " + " | ".join(
            f"{_pct(d[m]['Hit@1'], 1)} / {_pct(d[m]['Answer pass'], 1)}" for m in MODES) + " |")
    L += ["", "## Per question: rank of the first chunk on an expected page (blank = not in top 10)", "",
          "| ID | Type | " + " | ".join(MODES) + " |", "|---|---|" + "---|" * len(MODES)]
    for s in samples.load():
        if s["category"] == "none":
            continue
        cells = []
        for m in MODES:
            r = next(x for x in rows if x["id"] == s["id"] and x["mode"] == m)
            cells.append(("#%d" % r["rank_page"] if r["rank_page"] else "-") + ("" if r["ans_pass"] else " ❌"))
        L.append(f"| {s['id']} | {s['category']} | " + " | ".join(cells) + " |")
    L += ["", "❌ = the generated answer did not pass (missing key facts or no cited source on an expected page).", "",
          "**Notes**",
          "- *Hit@k*: the first chunk on an expected page is within the top k. *MRR*: average of 1/rank.",
          "- *Right doc @1* only requires the correct document, so it shows whether a method finds the document but not the page.",
          "- Only hybrid + semantic can refuse (it is the only one with a reranker score), so the others score 0% on out-of-scope by design.",
          "- Expected pages are anchor-based and can be narrower than every valid page, which understates scores for all methods equally."]
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(L))
    return summary, by_cat


if __name__ == "__main__":
    out = run(lambda p: print(f"\r{p * 100:3.0f}%", end="", file=sys.stderr))
    print(file=sys.stderr)
    summary, by_cat = write_markdown(out)
    print(open(OUT_MD, encoding="utf-8").read())
