"""RAG chat over the NIST PDFs: hybrid + semantic retrieval, keyless auth throughout."""
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from tracing import tracer  # must come before the SDK clients so they are instrumented
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from openai import RateLimitError
from azure.search.documents.models import VectorizableTextQuery

from config import (
    CHAT_DEPLOYMENT,
    MIN_RERANKER_SCORE,
    PROJECT_ENDPOINT,
    SEARCH_ENDPOINT,
    SEARCH_INDEX,
    SEMANTIC_CONFIG,
)

credential = DefaultAzureCredential()
chat_client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential).get_openai_client()
search_client = SearchClient(SEARCH_ENDPOINT, SEARCH_INDEX, credential)

SYSTEM_PROMPT = (
    "You answer questions using ONLY the numbered sources provided. "
    "Cite sources inline like [1] or [2][3]. If the sources do not contain the answer, "
    "say you could not find it in the documents. Be concise."
)


MODES = ["hybrid + semantic", "hybrid", "vector", "keyword"]

# Large PDFs were split into <=30-page parts named like "<doc>__p061-090.pdf". The index stores the page
# within the part, so the real PDF page is that page plus (part start - 1).
PART_RE = re.compile(r"^(?P<doc>.+?)(?:__p(?P<start>\d{3})-(?P<end>\d{3}))?\.pdf$")


def real_location(title: str, part_page):
    m = PART_RE.match(title)
    doc = m.group("doc") if m else title
    offset = int(m.group("start")) - 1 if m and m.group("start") else 0
    return doc, (part_page + offset if part_page is not None else None)


def retrieve(question: str, top: int = 5, mode: str = "hybrid + semantic"):
    kwargs = {"select": ["title", "chunk", "source", "page"], "top": top}
    if mode in ("hybrid + semantic", "hybrid", "keyword"):
        kwargs["search_text"] = question
    if mode in ("hybrid + semantic", "hybrid", "vector"):
        kwargs["vector_queries"] = [
            VectorizableTextQuery(text=question, k_nearest_neighbors=50, fields="text_vector")
        ]
    if mode == "hybrid + semantic":
        kwargs["query_type"] = "semantic"
        kwargs["semantic_configuration_name"] = SEMANTIC_CONFIG
    docs = []
    with tracer.start_as_current_span("rag.retrieve") as span:
        span.set_attribute("rag.mode", mode)
        span.set_attribute("rag.top", top)
        results = list(search_client.search(**kwargs))
        span.set_attribute("rag.hits", len(results))
        if results:
            span.set_attribute("rag.top_reranker", results[0].get("@search.reranker_score") or 0.0)
    for r in results:
        doc, page = real_location(r["title"], r.get("page"))
        docs.append(
            {
                "title": r["title"],
                "doc": doc,
                "page": page,
                "chunk": r["chunk"],
                "source": r["source"],
                "score": r["@search.score"],
                "reranker": r.get("@search.reranker_score"),
            }
        )
    return docs


def cite(d) -> str:
    return f"{d['doc']}, p.{d['page']}" if d["page"] is not None else d["doc"]


def chat_with_retry(messages, tries: int = 7):
    """Chat call that backs off on 429s (the deployment is capped at 50K tokens/minute)."""
    for attempt in range(tries):
        try:
            with tracer.start_as_current_span(f"chat {CHAT_DEPLOYMENT}") as span:
                span.set_attribute("gen_ai.operation.name", "chat")
                span.set_attribute("gen_ai.request.model", CHAT_DEPLOYMENT)
                span.set_attribute("rag.attempt", attempt + 1)
                resp = chat_client.chat.completions.create(model=CHAT_DEPLOYMENT, messages=messages, temperature=0)
                if resp.usage:
                    span.set_attribute("gen_ai.usage.input_tokens", resp.usage.prompt_tokens)
                    span.set_attribute("gen_ai.usage.output_tokens", resp.usage.completion_tokens)
                return resp
        except RateLimitError as e:
            if attempt == tries - 1:
                raise
            wait = min(30, 2 ** (attempt + 1))
            retry_after = getattr(getattr(e, "response", None), "headers", {}).get("retry-after")
            time.sleep(max(wait, float(retry_after)) if retry_after and retry_after.isdigit() else wait)


def answer(question: str, mode: str = "hybrid + semantic", top: int = 5):
    with tracer.start_as_current_span("rag.answer") as span:
        span.set_attribute("rag.mode", mode)
        span.set_attribute("rag.question", question)
        result = _answer(question, mode, top)
        span.set_attribute("rag.refused", result["refused"])
        return result


def _answer(question: str, mode: str, top: int):
    docs = retrieve(question, top=top, mode=mode)
    # The reranker score is only available in semantic mode, so the gate only applies there.
    if not docs or (mode == "hybrid + semantic" and docs[0]["reranker"] < MIN_RERANKER_SCORE):
        return {"text": "I couldn't find that in the documents.", "docs": docs, "usage": None, "refused": True}
    context = "\n\n".join(f"[{i}] ({cite(d)})\n{d['chunk']}" for i, d in enumerate(docs, 1))
    resp = chat_with_retry(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Sources:\n{context}\n\nQuestion: {question}"},
        ]
    )
    return {"text": resp.choices[0].message.content, "docs": docs, "usage": resp.usage, "refused": False}


def cited_indices(text: str):
    return sorted({int(n) for n in re.findall(r"\[(\d+)\]", text)})


def compare_modes(question: str, top: int = 5):
    """Run the question through all four retrieval modes in parallel, each with its own model answer."""

    def run(mode):
        t0 = time.perf_counter()
        r = answer(question, mode=mode, top=top)
        r.update(mode=mode, latency=time.perf_counter() - t0, cited=cited_indices(r["text"]))
        return r

    with ThreadPoolExecutor(max_workers=len(MODES)) as pool:
        return list(pool.map(run, MODES))


def main():
    question = " ".join(sys.argv[1:]) or input("Question: ")
    result = answer(question)
    print("\n" + result["text"])
    if not result["refused"]:
        print("\nSources:")
        for i, d in enumerate(result["docs"], 1):
            print(f"  [{i}] {cite(d)}  (reranker {d['reranker']:.2f})")


if __name__ == "__main__":
    main()
