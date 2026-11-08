# Replicate the lab, step by step

Run everything from the repo root in Git Bash (Windows) or any POSIX shell. Each step says what it does, why, and how
to check it worked. Do the steps in order.

## 0. Before you start

1. Install: Python 3.11+, Azure CLI, `curl`, Git.
2. Sign in to the tenant that owns your sandbox subscription: `az login` (add `--tenant <tenant-id>` if you have several).
   If your Owner access comes through a guest account or delegation, sign in with the account that actually holds the
   roles, otherwise role assignments fail with `AuthorizationFailed`. Check with `az role assignment list --assignee <you> --all`.
3. Copy `scripts/00-env.sh.example` to `scripts/00-env.sh` and edit it. **Pick `SUF` once and hard-code it**, because a
   new random value in a new shell points at resources that don't exist.
4. `source scripts/00-env.sh`
5. Create a venv and install: `python -m venv .venv && . .venv/Scripts/activate && pip install -r app/requirements.txt`
6. Download the 20 PDFs into `./pdfs` using the names in [pdf-list.md](pdf-list.md).

**Region check.** `LOC` needs `gpt-4.1-mini` and `text-embedding-3-small` as `GlobalStandard`. List what is offered with
`az cognitiveservices model list -l $LOC`. Search Basic capacity varies by region: we couldn't create it in eastus2 and used
eastus, which is fine because the services talk over the network anyway.

## Steps 1-3: resources and documents

```bash
bash scripts/01-provision.sh
```

What it creates, and why:

| Resource | Purpose |
|---|---|
| Resource group (tagged) | One thing to delete at the end. Tags carry owner and purpose, which many organizations enforce with Azure Policy |
| Foundry resource (`AIServices`) + **project** | The resource holds the models. The project is the endpoint your app connects to |
| `chat` deployment (gpt-4.1-mini) | Writes the answers |
| `embedding` deployment (text-embedding-3-small) | Turns text into vectors, for the indexer and for query-time vectorizing |
| AI Search (Basic) with a system-assigned identity | The index plus the indexer that does the ingestion work |
| Storage account (shared key disabled) | Holds the PDFs. Entra only |
| Role assignments for **you** | Search Service Contributor + Search Index Data Contributor, Cognitive Services OpenAI User, Foundry User, Storage Blob Data Contributor |
| Role assignments for the **Search identity** | OpenAI User (embeddings), Cognitive Services User (Layout skill), Storage Blob Data Reader (read PDFs) |

The Search service's own identity needs roles too. That is the part people miss: it is the indexer, not you, that reads the
blobs and calls the models.

**Check:** `az role assignment list --scope $(az group show -n $RG --query id -o tsv) -o table` shows the assignments.
They can take a few minutes to start working.

Then upload the documents:

```bash
bash scripts/02-upload-pdfs.sh
```

This splits every PDF into parts of at most 30 pages (`<doc>__p031-060.pdf`) and uploads them. Why split? The Document
Layout skill has a 5-minute per-document timeout and big PDFs hit it. The app converts "page 3 of part p031-060" back to
the real page 33 using the part name. **Check:** it should report 58 parts and 1,439 pages for the NIST set.

## Steps 2 and 4: index, skillset, indexer

```bash
bash scripts/03-search-objects.sh
```

The four JSON definitions in `infra/search/` are the core of the lab. Read them:

- **index** (`index.template.json`): fields `chunk`, `title`, `page`, `source` and a 1536-dimension `text_vector`. The vector
  profile points to an Azure OpenAI **vectorizer**, so queries can send plain text and Search embeds it for you. The
  `semantic` block defines the configuration used by the reranker.
- **data source** (`datasource.template.json`): points at the blob container using a `ResourceId=` connection string. No
  key, so Search uses its managed identity.
- **skillset** (`skillset.template.json`): (1) the **Document Intelligence Layout skill** reads each PDF and returns text
  chunks of about 2,000 characters with 200 overlap, each with its `pageNumber`; (2) the **embedding skill** vectorizes each chunk;
  (3) **index projections** write one search document per chunk and map page, title and source.
  `AIServicesByIdentity` bills the Layout skill to your Foundry resource using Search's identity, which requires API version `2026-04-01`.
- **indexer** (`indexer.template.json`): ties data source, skillset and index together. Creating it starts the first run.

Monitor with `bash scripts/04-indexer-status.sh`. Expect 2,704 chunks when finished.

> **Do not delete, reset or re-create the indexer.** Layout is billed per page processed, so a re-run bills everything
> again. The indexer tracks changes, so adding or updating a PDF later only processes that file.

Runs can show `inProgress` with no new chunks for long stretches and then resume by themselves. Ours took about an hour
or two overall. You can't cancel a run; a `409 Another invocation in progress` just means it is still going.

## Step 6: connect the app

```bash
cd app
python ping.py          # one keyless chat call through the project SDK
```

`ping.py` is the smallest possible app: `AIProjectClient(endpoint, DefaultAzureCredential()).get_openai_client()` then a
normal chat completion. If it fails with a 401/403, you are missing the **Foundry User** role on the Foundry resource or
haven't waited for propagation.

Then ask a question: `python app.py "What does zero trust mean?"` and open the UI:

```bash
streamlit run ui.py --server.address localhost
```

Always pass `--server.address localhost`. Streamlit's default exposes the app to your whole network, and this app runs with your identity.

## Step 5: compare the four retrieval methods

In the UI, open **Compare 4 methods**, pick a sample question and click Run. Same question goes through:

| Method | How it works | Good at |
|---|---|---|
| keyword | BM25 on the words | exact terms, codes, names |
| vector | nearest chunks by meaning | paraphrases |
| hybrid | keyword + vector merged with Reciprocal Rank Fusion | covering both |
| hybrid + semantic | hybrid, then a language model re-ranks the top results and gives a 0-4 score | best ordering, refusal gate |

Look at which page each method ranks first and which sources the answer actually cited.

## Step 8: citations and the refusal gate

Read `retrieve()` and `answer()` in `app/app.py`. Three ideas to understand:

1. Every chunk carries `title` (the part file name) and `page` (page within the part). `real_location()` converts to the real document and page.
2. The prompt numbers the sources `[1]..[5]` and tells the model to cite them. `cited_indices()` finds which were used.
3. In semantic mode, if the top reranker score is below `MIN_RERANKER_SCORE` (2.0), the app refuses *before* calling the chat model.
   In our tests answerable questions scored 2.5-3.4 and unanswerable ones about 0.9-1.0. Tune it for your data in the UI sidebar.

## Step 7: lock it down

After everything works:

```bash
bash scripts/05-lockdown-and-tracing.sh   # disables key auth on Foundry and Search, creates App Insights (step 9)
```

Re-run `python ping.py` and an app question. They must still work, because the app never used keys. To prove the lock-down,
call Search with a bogus `api-key` header: it should be rejected.

## Step 9: tracing

The script prints an `export APPLICATIONINSIGHTS_CONNECTION_STRING=...` line. Run it, restart the app, ask a few questions
(include one out-of-scope), wait a few minutes, then in the portal open your Application Insights resource, **Transaction search**, filter on `rag.`:

- `rag.answer`: the whole request, with mode, question and whether it refused
- `rag.retrieve`: the search step, with hit count and top reranker score
- `chat chat`: the model call, with input and output token counts and its duration as latency

Traces take a few minutes to appear. To query from the CLI use `az rest` against the component's `/query` endpoint.

## Score the methods

```bash
cd app
python run_samples.py            # 15 sample questions through hybrid + semantic, writes SAMPLE_QUESTIONS.md
python scorecard.py              # all four methods, writes SCORECARD.md (about 60 searches and model calls, a few minutes)
```

The expected pages in `samples.py` are found by searching the original PDFs for anchor text, not by asking the index, so the
test isn't circular. If you use different PDFs, rewrite `SAMPLES` (see [CUSTOMIZE.md](CUSTOMIZE.md)).

The chat deployment is capped at 50K tokens per minute, so the scorecard uses 3 workers and `chat_with_retry` backs off on 429s.

## Clean up

```bash
az group delete -n "$RG" --yes --no-wait
```
