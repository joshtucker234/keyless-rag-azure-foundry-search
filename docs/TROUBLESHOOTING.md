# Troubleshooting and gotchas

Every item below happened to us while building this.

| Symptom | Cause | Fix |
|---|---|---|
| `AuthorizationFailed` on role assignment | You are signed in as an identity that has no write access (for example, the managing tenant of a delegated subscription) | Sign in with the account that is Owner on the subscription |
| Resource creation denied by policy | Tag policy requires non-empty `Owner` and `Purpose` tags | Pass both. Projects have no `--tags`, so create them with `az rest` (the script does) |
| `az search service create` fails for capacity | The region has no Basic capacity | Use another region for `SEARCH_LOC` |
| Skillset rejected: `AIServicesByIdentity` unknown | Older API version | Use `api-version=2026-04-01` |
| `az search service update --disable-local-auth` fails | `authOptions` must be null when local auth is disabled | The CLI flag handles it. In REST send `"authOptions": null` in the same PATCH |
| Layout skill timeouts on big PDFs | 5-minute per-document limit | Split to 30 pages or fewer (`split_pdfs.py`) |
| Indexer `inProgress` for a long time, zero new chunks | Normal for big enrichment runs. It resumes by itself | Wait. Don't delete, reset or re-save the indexer; you can't cancel a run and a re-run re-bills pages |
| Status history doesn't show the running run | The in-progress run is only under `lastResult` | Read `lastResult` in the status |
| 401/403 from the app after provisioning | Role propagation, or a missing role | Wait a few minutes. Needed: **Foundry User** (project SDK) and **Cognitive Services OpenAI User** on the Foundry resource, plus the Search roles |
| 403 from the indexer | The **Search service's identity** is missing a role | OpenAI User, Cognitive Services User on Foundry; Storage Blob Data Reader on storage |
| 429 from chat | 50K tokens-per-minute deployment cap hit by parallel calls | `chat_with_retry` backs off. Lower parallelism or raise the deployment capacity |
| Citations show page 1-30 on every long document | You are reading the page within the part | Use `real_location()`: real page = part page + part start - 1 |
| Page numbers don't match the printed page labels | Pages are PDF page indexes, not printed labels | Expected. Front matter shifts the numbers |
| Streamlit is reachable from other machines | Default bind address | Always `--server.address localhost` |
| No traces in Application Insights | Missing **Monitoring Metrics Publisher** role, or wait time | Grant the role to yourself on the component and wait a few minutes. Run with exporter debug logging to see `Transmission succeeded` |
| `ModuleNotFoundError: opentelemetry.util.genai.instruments` | The released OpenAI instrumentor and `util-genai` packages were out of sync | We skipped that instrumentor and record token counts in our own `chat` span (see `app/app.py`) |
| Commands fail with odd `C:/Program Files/Git/...` paths | Git Bash rewrites paths starting with `/` | `export MSYS_NO_PATHCONV=1` (in `00-env.sh`) |
| Scripts use `/tmp` | Not present on some Windows setups | Git Bash provides it. In PowerShell use `$env:TEMP` |

## Not verified

- The scripts are assembled from the commands we ran and checked for syntax. `split_pdfs.py` and the JSON templates were
  tested locally. A fresh end-to-end run from the scripts has **not** been done, so expect small fixes and send a PR.
- Prices are list-price estimates from the Azure retail price API at the time. The real bill may differ.
- Exact reranker scores and ranks will vary slightly with service updates.
