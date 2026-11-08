# Make it your own

The lab is deliberately small. These are the knobs and the next experiments, roughly in order of learning value.

## Settings you can change without touching code

| What | Where | Try |
|---|---|---|
| Chat model | `az cognitiveservices account deployment create` in `01-provision.sh`, `CHAT_DEPLOYMENT` env var | A larger model for better answers, or a smaller one for cost. Compare in the scorecard |
| Embedding model | `index.template.json` (`dimensions`, `modelName`) and `skillset.template.json` | `text-embedding-3-large` (3072 dimensions). Changing it means a new index and a full re-index (and re-billed Layout pages, unless you cache enrichments) |
| Chunk size / overlap | `skillset.template.json` → `chunkingProperties` | 1000/100 or 3000/300. Smaller chunks give more precise pages but lose context. Re-measure with the scorecard |
| Top-k sent to the model | UI sidebar, `top` in `app.answer()` | 3 vs 5 vs 8: watch accuracy against prompt tokens in the traces |
| Refusal cutoff | UI sidebar, `MIN_RERANKER_SCORE` | Raise it to refuse more, lower it to answer more. Check both sample refusals and answerable questions |
| Vector search settings | `index.template.json` (`m`, `efConstruction`, `efSearch`), `k_nearest_neighbors` in `app.retrieve()` | Larger `k` finds more candidates for hybrid to merge |
| System prompt | `SYSTEM_PROMPT` in `app/app.py` | Change the citation style, tone, or add "answer in bullet points". Re-run the samples |
| Region and SKUs | `00-env.sh` | Any region with the two models. Search Basic is the cheapest tier with semantic ranking |

## Use your own documents

1. Put any PDFs in `./pdfs`, run `02-upload-pdfs.sh`, and let the indexer run. Keep non-sensitive content only.
2. Delete `app/samples_resolved.json` and rewrite `SAMPLES` in `app/samples.py`. Each sample has:
   - `question` and `category` (`exact`, `paraphrase`, `neighbor`, or `none` for should-refuse)
   - `docs`: part of the file name of the document that should answer it
   - `anchors`: regexes that find the answer text in the original PDF. `resolve()` turns them into expected page numbers
   - `key_points`: regexes the answer must contain
3. Write at least 5 questions per category, **including paraphrases that avoid the document's own wording** and a few unanswerable
   ones. That is where the retrieval methods separate.
4. Run `python scorecard.py` before and after each change.

Other formats: Search can also index Office files, HTML and images. The Layout skill handles PDFs, images and Office documents.

## Stretch exercises

1. **Fix the failing question.** The minimum-password-length question (S04) fails for every method because the key sentence
   isn't in the top 5. Investigate the chunk that contains it, then try smaller chunks, a larger top-k, or a query rewrite step
   (ask the model to expand the question into search terms first). Prove the fix with the scorecard.
2. **Private endpoint.** Put Search (and optionally Foundry and Storage) behind private endpoints and run the app from inside the VNet.
3. **A real test set.** Grow the sample library to 50 questions, and add a second judge: have a model grade each answer for
   groundedness against its cited chunks.
4. **Filtering.** Add a `doc` filter to the UI (the `title` field is filterable) so users can restrict the search to one document.
5. **Freshness.** Point the data source at a changing container and schedule the indexer. Watch only changed files get reprocessed.
   (For SharePoint, look at the SharePoint Online indexer, which is a preview feature.)
6. **Agentic retrieval.** Replace the single query with the Search agentic retrieval / knowledge base features and compare answers.
7. **Evaluations.** Run the Foundry evaluators (groundedness, relevance) over the sample answers and trace the results.
8. **Cost control.** Turn on enrichment caching for the skillset so changing a downstream skill doesn't re-bill the Layout step.
9. **Another interface.** Wrap `app.answer()` in a FastAPI endpoint and deploy it to Azure Container Apps with a managed identity.

## Things to keep as-is

- Never add API keys to make something "just work". If a call fails with 401/403, the answer is a missing role.
- Keep the `--server.address localhost` for Streamlit.
- Keep documents public or synthetic in this lab.
