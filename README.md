# Keyless RAG chat app on Microsoft Foundry + Azure AI Search

A hands-on lab. You build a Python chat app that answers questions over 20 public NIST PDFs, **cites the
document and page for every answer**, and uses **no keys anywhere** (Microsoft Entra identities and RBAC only). Along
the way you compare four retrieval methods with a real scorecard and trace every call in Application Insights.

I built it as a hands-on way to learn Microsoft Foundry, Azure AI Search and Azure observability, and you can follow it
yourself to learn the same tools by building something real.

| | |
|---|---|
| **Time** | About half a day of hands-on work, plus 1-2 hours of waiting for the indexer |
| **Cost** | Roughly **$15-20** in total. Search Basic is about $2.50/day and the Document Layout skill is about $14 for 1,440 pages (list price, see [Cost](#cost-and-cleanup)). **Delete the resource group when done.** |
| **You need** | An Azure subscription where you can create resources and assign RBAC roles (Owner, or Contributor plus User Access Administrator), Python 3.11+, Azure CLI, Git Bash or any POSIX shell |
| **Skills** | Foundry project SDK, embeddings and chat deployments, AI Search indexers and skillsets, vector / keyword / hybrid / semantic retrieval, managed-identity RBAC, tracing |

## What I built and what it uses

| Piece | Technology |
|---|---|
| Models | Microsoft Foundry project with `gpt-4.1-mini` (chat) and `text-embedding-3-small` (embeddings) |
| Retrieval | Azure AI Search Basic: vector (HNSW), keyword (BM25), hybrid (RRF) and semantic ranker, with an integrated vectorizer |
| Ingestion | Search indexer + skillset: Document Intelligence Layout skill (page-aware chunks), Azure OpenAI embedding skill, index projections |
| Storage | Blob storage, Entra-only (shared keys off) |
| App | Python, `azure-ai-projects`, `azure-search-documents`, Streamlit UI |
| Security | `DefaultAzureCredential` everywhere, managed identity for Search, RBAC roles, key auth disabled on every service |
| Observability | OpenTelemetry to Application Insights (Entra-authenticated ingestion) |
| Evaluation | Home-made scorecard: Hit@k, MRR, answer pass rate over a ground-truth question set |

## What you end up with

```
                         ┌──────────────────────────────┐
  You ──► Streamlit UI ──►  Python app (DefaultAzureCredential, no keys)
          (localhost)    └──────┬───────────────┬───────┘
                                │               │ OpenTelemetry spans
                  Foundry project SDK           ▼
                                │        Application Insights
              ┌─────────────────┴──────────┐   (tokens, latency, mode, refusals)
              ▼                            ▼
   Chat model (gpt-4.1-mini)     Azure AI Search index  ◄── vectorizer ── Embedding model
                                 vector + keyword + semantic                (text-embedding-3-small)
                                        ▲
                                        │ indexer + skillset
                                        │ (Document Layout → chunks with page numbers → embed)
                                  Blob storage: PDFs
```

The app:

1. Takes a question and retrieves the best chunks from the index. You pick the method: **hybrid + semantic**,
   hybrid, vector or keyword.
2. Sends the top chunks to the chat model with an instruction to answer only from them and cite as `[1]`, `[2]`.
3. Shows the answer with sources as `document, p.N`. The page is the real PDF page index.
4. **Refuses** ("I couldn't find that in the documents") when the semantic reranker's top score is below a cutoff,
   so out-of-scope questions don't get invented answers.

The web UI has four tabs: **Ask**, **Compare 4 methods** (same question, four answers and four source lists side by
side), **Sample library** (questions with the answer, source and page you should expect) and **Scorecard**.

## The steps

Each step maps to a line of the lab and to a script. Details and commands are in [docs/REPLICATE.md](docs/REPLICATE.md).

| # | What you do | What it teaches | Script |
|---|---|---|---|
| 1 | Create a Foundry project and deploy a chat model and an embedding model | Foundry resource vs project, model deployments, GlobalStandard capacity | `01-provision.sh` |
| 2 | Create an AI Search service and an index with a vector field | Index schema, HNSW, vectorizer, semantic configuration | `01-provision.sh`, `03-search-objects.sh` |
| 3 | Upload the PDFs to Blob storage | Entra-only storage, why we split large PDFs | `02-upload-pdfs.sh` |
| 4 | Build the indexer and skillset | Document Layout skill, chunking, embedding skill, index projections | `03-search-objects.sh`, `04-indexer-status.sh` |
| 5 | Query with vector, keyword, hybrid and hybrid + semantic | How each method behaves, reranker scores | `app/app.py`, UI **Compare** tab |
| 6 | Connect the Python app with the project SDK | `AIProjectClient`, `get_openai_client()`, `DefaultAzureCredential` | `app/ping.py`, `app/app.py` |
| 7 | Assign RBAC roles, then turn keys off | Least-privilege roles for you **and** for the Search managed identity | `01-provision.sh`, `05-lockdown-and-tracing.sh` |
| 8 | Return answers with citations to source pages | Page-aware chunking, mapping part pages to real pages, refusal gate | `app/app.py`, `app/samples.py` |
| 9 | Enable tracing and inspect tokens and latency per call | OpenTelemetry to Application Insights with Entra auth | `05-lockdown-and-tracing.sh`, `app/tracing.py` |
| + | Score the four methods | Hit@k, MRR, answer pass rate, why small test sets mislead | `app/scorecard.py` |

## Results we got (use these to sanity-check your build)

13 answerable questions plus 2 out-of-scope, each run through all four methods against the 20 NIST PDFs
(full tables in [results/SCORECARD.md](results/SCORECARD.md), questions in [results/SAMPLE_QUESTIONS.md](results/SAMPLE_QUESTIONS.md)).

| Method | Right page ranked #1 | Right page in top 3 | MRR | Answer passes | Refuses out-of-scope |
|---|---|---|---|---|---|
| **hybrid + semantic** | **85%** | 85% | **0.87** | **92%** | **100%** |
| vector | 77% | 85% | 0.82 | 85% | no (cannot) |
| hybrid | 69% | 92% | 0.81 | 85% | no (cannot) |
| keyword | 62% | 69% | 0.69 | 77% | no (cannot) |

What to take from it:

- **Hybrid + semantic is the best default**, and it is the only method that produces a reranker score, so it is the
  only one that can say "not in the documents".
- **Hybrid and vector find the right document every time but often rank the exact page lower**. Semantic re-ranking
  mostly fixes the page order.
- **Keyword is weakest on paraphrased questions** (it matches words, not meaning).
- **It is not uniformly better.** On one question semantic ranking put the right document second.
- **Be skeptical of small samples.** With 13 questions one question is about 8 points, so treat 1-2 question gaps
  as noise. Your numbers will differ a little, and model wording varies run to run.
- **One question (minimum password length) fails for every method.** The right sentence is never in the top 5. That
  is a chunking problem, not a search-method problem, and it makes a good [stretch exercise](docs/CUSTOMIZE.md#stretch-exercises).

## Quick start

```bash
git clone https://github.com/joshtucker234/keyless-rag-azure-foundry-search && cd keyless-rag-azure-foundry-search
cp scripts/00-env.sh.example scripts/00-env.sh      # edit: subscription, your email, a fixed SUF
source scripts/00-env.sh
az login && bash scripts/01-provision.sh            # Foundry, models, Search, Storage, RBAC
# download the PDFs into ./pdfs (docs/pdf-list.md), then:
python -m venv .venv && . .venv/Scripts/activate    # Linux/macOS: . .venv/bin/activate
pip install -r app/requirements.txt
bash scripts/02-upload-pdfs.sh && bash scripts/03-search-objects.sh
bash scripts/04-indexer-status.sh                   # repeat until it finishes (can take 1-2 hours)
cd app && python ping.py && streamlit run ui.py --server.address localhost
```

Read [docs/REPLICATE.md](docs/REPLICATE.md) before running anything: it explains what each step does and what to check.

## Repo layout

```
app/              Python app: retrieval + answer (app.py), Streamlit UI (ui.py), sample library, scorecard, tracing
infra/search/     Search index, data source, skillset and indexer definitions (templates with placeholders)
scripts/          Numbered scripts that provision and configure everything (Azure CLI + curl, no keys)
docs/             REPLICATE.md (walkthrough), CUSTOMIZE.md (ideas and knobs), TROUBLESHOOTING.md, pdf-list.md
results/          The scorecard and sample questions from our run
```

## Security notes

- **No secrets in this repo and none are needed.** Everything authenticates with `DefaultAzureCredential`. Key auth is
  switched off on Foundry, Search, Storage and Application Insights at the end of the lab.
- `scripts/00-env.sh` holds your subscription ID and email. It is git-ignored. Do not commit it.
- The PDFs are public NIST documents, downloaded by you, and not stored in this repo.
- Do not put customer or confidential documents in this lab. Use the pattern, not the data.

## Cost and cleanup

| Item | Approx. cost |
|---|---|
| Azure AI Search Basic | about $2.50 per day while it exists |
| Document Layout skill | about $10 per 1,000 pages. The corpus is about 1,440 pages, so about $14. You pay when a page is processed, so a reset or re-created indexer pays again |
| Chat and embedding calls | cents for this corpus |
| Application Insights / Log Analytics | pennies at lab volume |

These are list-price estimates, not billed amounts. Check **Cost Management** for your resource group.

**When you are done, delete the resource group:** `az group delete -n "$RG" --yes --no-wait`

## Contributing

Found a step that doesn't work, a better setting, or a new region quirk? Open a PR or an issue. The scripts were
assembled from the commands used in the original build and checked for syntax, but a clean end-to-end run by a new
person is the real test, so please report what you hit. See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

Author: Josh Tucker ([@joshtucker234](https://github.com/joshtucker234)).
