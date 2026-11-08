"""Streamlit UI for the Lab 1 RAG app. Run: streamlit run ui.py"""
import json
import os
import re
import time

import streamlit as st

import app
import samples
import scorecard
from app import MODES

st.set_page_config(page_title="Keyless RAG on Foundry", page_icon="🔎", layout="wide")
st.title("🔎 RAG over NIST PDFs")
st.caption("Keyless auth (DefaultAzureCredential) · Foundry project SDK · Azure AI Search · pages are PDF page indexes")

SAMPLES = samples.load()
BY_ID = {s["id"]: s for s in SAMPLES}


def pages_text(sample):
    if not sample["docs"]:
        return "none: the app should refuse"
    out = []
    for sub, pg in sample["expected_pages"].items():
        shown = ", ".join(map(str, pg[:10])) + (", ..." if len(pg) > 10 else "")
        out.append(f"**{sub}** p.{shown}")
    return " · ".join(out)


def render_sources(docs, cited, sample=None, key=""):
    """List retrieved chunks. ✅ = cited in the answer, 🎯 = on an expected page (sample library only)."""
    if not docs:
        st.caption("No sources retrieved.")
    for i, d in enumerate(docs, 1):
        marks = ("✅" if i in cited else "▫️") + (" 🎯" if sample and sample["docs"] and samples.source_ok(sample, d) else "")
        rr = f" · rerank {d['reranker']:.2f}" if d["reranker"] is not None else ""
        with st.expander(f"{marks} [{i}] {app.cite(d).replace('NIST-', '')}{rr}"):
            st.caption(f"search score {d['score']:.3f}")
            st.write(d["chunk"])


def render_compare(question, sample=None, key="cmp"):
    """Run all four retrieval methods, each with its own answer, and show them side by side."""
    with st.spinner("Running all four methods (4 searches + 4 model answers)..."):
        t0 = time.perf_counter()
        results = app.compare_modes(question)
        total = time.perf_counter() - t0
    base = {(d["doc"], d["page"]) for d in results[0]["docs"]}
    rows = []
    for r in results:
        docs, cited = r["docs"], r["cited"]
        top = app.cite(docs[0]).replace("NIST-", "") if docs else "-"
        shared = len({(d["doc"], d["page"]) for d in docs} & base)
        row = {
            "Method": r["mode"],
            "Top-1 source": top,
            "Cited": ", ".join(app.cite(docs[i - 1]).replace("NIST-", "") for i in cited if 0 < i <= len(docs)) or "-",
            "Shared pages w/ hybrid+semantic": f"{shared}/{len(docs)}" if docs else "-",
            "Answered": "refused" if r["refused"] else "yes",
            "Latency": f"{r['latency']:.1f}s",
        }
        if sample and sample["docs"]:
            row["Top-1 on expected page"] = "🎯 yes" if docs and samples.source_ok(sample, docs[0]) else "no"
            row["Any source on expected page"] = "🎯 yes" if any(samples.source_ok(sample, d) for d in docs) else "no"
            row["Key points in answer"] = "yes" if all(re.search(k, r["text"], re.I) for k in sample["key_points"]) else "no"
        rows.append(row)
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption(f"All four ran in parallel in {total:.1f}s. The refusal gate only applies to hybrid + semantic, because only "
               "it produces a reranker score; the other three always send their results to the model.")
    cols = st.columns(len(results))
    for col, r in zip(cols, results):
        with col:
            st.subheader(r["mode"])
            if r["refused"]:
                st.warning(r["text"])
            else:
                st.markdown(r["text"])
            st.markdown("**Sources** (✅ cited · ▫️ retrieved only" + (" · 🎯 expected page)" if sample and sample["docs"] else ")"))
            render_sources(r["docs"], r["cited"], sample)


with st.sidebar:
    st.header("Settings")
    mode = st.selectbox("Retrieval mode (Ask tab)", MODES, help="hybrid + semantic scored best in testing")
    top = st.slider("Chunks sent to the model", 1, 10, 5)
    cutoff = st.slider(
        "Reranker cutoff (semantic only)", 0.0, 4.0, float(app.MIN_RERANKER_SCORE), 0.1,
        help="Below this top score the app refuses to answer. Answerable questions scored 2.5-3.4, unanswerable ~1.0.",
    )
    app.MIN_RERANKER_SCORE = cutoff
    st.divider()
    st.caption("Tabs: **Ask** one question · **Compare 4 methods** side by side · **Sample library** with expected answers.")

tab_ask, tab_cmp, tab_lib, tab_score = st.tabs(["Ask", "Compare 4 methods", "Sample library", "Scorecard"])

with tab_ask:
    question = st.text_input("Question", key="q", placeholder="Ask something about the NIST documents...")
    if question:
        t0 = time.perf_counter()
        with st.spinner("Searching and answering..."):
            result = app.answer(question, mode=mode, top=top)
        elapsed = time.perf_counter() - t0
        if result["refused"]:
            st.warning(result["text"])
        else:
            st.markdown(result["text"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mode", mode)
        c2.metric("Latency", f"{elapsed:.1f}s")
        if result["usage"]:
            c3.metric("Prompt tokens", result["usage"].prompt_tokens)
            c4.metric("Completion tokens", result["usage"].completion_tokens)
        st.subheader("Retrieved chunks")
        render_sources(result["docs"], app.cited_indices(result["text"]))

with tab_cmp:
    st.write("Same question, all four retrieval methods. Each gets its own answer and cited sources.")
    pick = st.selectbox("Load a sample question (optional)", ["(type my own)"] + [f"{s['id']} · {s['question']}" for s in SAMPLES])
    default_q = BY_ID[pick.split(" · ")[0]]["question"] if pick != "(type my own)" else ""
    cq = st.text_input("Question to compare", value=default_q, key=f"cq_{pick}")
    if st.button("Run all 4 methods", type="primary", disabled=not cq):
        sample = BY_ID[pick.split(" · ")[0]] if pick != "(type my own)" and cq == default_q else None
        render_compare(cq, sample)

with tab_lib:
    st.write("Questions with the answer, source and pages you should expect. Expected pages come from searching the original "
             "PDFs, not from the search index. Several terms appear on many pages, so any listed page counts.")
    if st.button("Run the whole library (hybrid + semantic)"):
        table, passed = [], 0
        bar = st.progress(0.0)
        for n, s in enumerate(SAMPLES, 1):
            r = app.answer(s["question"], mode="hybrid + semantic")
            c = samples.check(s, r)
            passed += c["passed"]
            table.append({"ID": s["id"], "Type": s["category"], "Question": s["question"],
                          "Result": "✅ pass" if c["passed"] else "❌ fail",
                          "Top source": app.cite(r["docs"][0]).replace("NIST-", "") if r["docs"] and not r["refused"] else "refused"})
            bar.progress(n / len(SAMPLES))
        st.success(f"{passed} of {len(SAMPLES)} passed")
        st.dataframe(table, hide_index=True, width="stretch")
    st.divider()
    choice = st.selectbox("Pick a sample", [f"{s['id']} · [{s['category']}] {s['question']}" for s in SAMPLES])
    s = BY_ID[choice.split(" · ")[0]]
    st.markdown(f"**Question:** {s['question']}")
    st.markdown(f"**Type:** {s['category']}")
    st.markdown(f"**Expect:** {s['expect']}")
    st.markdown(f"**Expected source:** {pages_text(s)}")
    a, b = st.columns(2)
    run_one = a.button("Run this question (hybrid + semantic)")
    run_cmp = b.button("Compare all 4 methods on this question")
    if run_one:
        with st.spinner("Running..."):
            r = app.answer(s["question"], mode="hybrid + semantic")
        c = samples.check(s, r)
        st.markdown(f"### {'✅ Pass' if c['passed'] else '❌ Fail'}")
        if r["refused"]:
            st.warning(r["text"])
        else:
            st.markdown(r["text"])
        if s["category"] != "none":
            st.write(f"- Top-1 source on an expected page: **{c['top1_source']}**\n"
                     f"- Any retrieved source on an expected page: **{c['any_retrieved']}**\n"
                     f"- A cited source on an expected page: **{c['cited_source']}**\n"
                     f"- All key points in the answer: **{c['key_points']}**")
        else:
            st.write(f"- Refused as expected: **{c['refused']}**")
        render_sources(r["docs"], app.cited_indices(r["text"]), s)
    if run_cmp:
        render_compare(s["question"], s)

with tab_score:
    st.write("Scores all four methods on the sample library: retrieval (did the right page show up, and how high) and "
             "answers (right facts, cited an expected page). Re-running makes about 60 searches and model calls and takes a few minutes.")
    if st.button("Run the scorecard now"):
        bar = st.progress(0.0, text="Scoring...")
        scorecard.run(lambda p: bar.progress(p, text=f"Scoring... {p * 100:.0f}%"))
        scorecard.write_markdown(json.load(open(scorecard.OUT_JSON)))
        bar.empty()
    if os.path.exists(scorecard.OUT_JSON):
        data = json.load(open(scorecard.OUT_JSON))
        summary, by_cat = scorecard.aggregate(data["rows"])
        n = summary[MODES[0]]["n"]
        st.caption(f"Last run: {data['generated']} · {n} answerable questions + 2 out-of-scope. One question is worth "
                   f"~{100 / n:.0f} points, so treat gaps of 1-2 questions as noise.")
        pct = lambda x: f"{100 * x:.0f}%"
        st.subheader("Retrieval (top 10 chunks, page level)")
        st.dataframe([{"Method": m, "Hit@1": pct(summary[m]["Hit@1"]), "Hit@3": pct(summary[m]["Hit@3"]),
                       "Hit@5": pct(summary[m]["Hit@5"]), "Hit@10": pct(summary[m]["Hit@10"]),
                       "MRR": f"{summary[m]['MRR']:.2f}", "Right doc @1": pct(summary[m]["Right doc @1"])} for m in MODES],
                     hide_index=True, width="stretch")
        st.bar_chart({"Hit@1": {m: summary[m]["Hit@1"] for m in MODES}, "Hit@3": {m: summary[m]["Hit@3"] for m in MODES},
                      "Answer pass": {m: summary[m]["Answer pass"] for m in MODES}})
        st.subheader("Answers (top 5 sent to the model)")
        st.dataframe([{"Method": m, "Key facts": pct(summary[m]["Key facts in answer"]),
                       "Cited expected page": pct(summary[m]["Cited expected page"]),
                       "Answer pass": pct(summary[m]["Answer pass"]),
                       "Refused out-of-scope": pct(summary[m]["Refused out-of-scope"]),
                       "Avg latency": f"{summary[m]['Avg latency (s)']:.1f}s"} for m in MODES],
                     hide_index=True, width="stretch")
        st.caption("Only hybrid + semantic can refuse (it is the only one with a reranker score), so the others score 0% there by design.")
        st.subheader("By question type (Hit@1 / Answer pass)")
        st.dataframe([{"Type (n)": f"{cat} ({d[MODES[0]]['n']})", **{m: f"{pct(d[m]['Hit@1'])} / {pct(d[m]['Answer pass'])}" for m in MODES}}
                      for cat, d in by_cat.items()], hide_index=True, width="stretch")
        st.subheader("Per question: rank of the first chunk on an expected page")
        qrows = []
        for smp in SAMPLES:
            if smp["category"] == "none":
                continue
            row = {"ID": smp["id"], "Type": smp["category"], "Question": smp["question"][:60]}
            for m in MODES:
                r = next(x for x in data["rows"] if x["id"] == smp["id"] and x["mode"] == m)
                row[m] = ("#%d" % r["rank_page"] if r["rank_page"] else "-") + ("" if r["ans_pass"] else " ❌")
            qrows.append(row)
        st.dataframe(qrows, hide_index=True, width="stretch")
        st.caption("❌ = the generated answer did not pass. '-' = no chunk on an expected page in the top 10.")
    else:
        st.info("No scorecard yet. Click the button above.")
