# Lab 1 retrieval scorecard

Generated 2026-11-07 18:09:42 from the sample library: **13 answerable questions** and 2 out-of-scope questions, each run through all four methods.

**Caution:** with only 13 questions, one question is worth about 8 points. Treat gaps of 1-2 questions as noise.

## Retrieval (top 10 chunks, page level)

| Method | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR | Right doc @1 |
|---|---|---|---|---|---|---|
| hybrid + semantic | 85% | 85% | 92% | 100% | 0.87 | 92% |
| hybrid | 69% | 92% | 92% | 100% | 0.81 | 100% |
| vector | 77% | 85% | 85% | 100% | 0.82 | 100% |
| keyword | 62% | 69% | 85% | 92% | 0.69 | 92% |

## Answers (top 5 sent to the model)

| Method | Key facts | Cited expected page | Answer pass | Refused out-of-scope | Avg latency |
|---|---|---|---|---|---|
| hybrid + semantic | 100% | 92% | 92% | 100% | 7.4s |
| hybrid | 92% | 92% | 85% | 0% | 5.1s |
| vector | 100% | 85% | 85% | 0% | 4.9s |
| keyword | 85% | 85% | 77% | 0% | 6.5s |

## By question type (Hit@1 / Answer pass)

| Type (n) | hybrid + semantic | hybrid | vector | keyword |
|---|---|---|---|---|
| exact (3) | 67% / 67% | 67% / 67% | 67% / 67% | 67% / 67% |
| neighbor (2) | 100% / 100% | 100% / 100% | 50% / 100% | 100% / 100% |
| paraphrase (8) | 88% / 100% | 62% / 88% | 88% / 88% | 50% / 75% |

## Per question: rank of the first chunk on an expected page (blank = not in top 10)

| ID | Type | hybrid + semantic | hybrid | vector | keyword |
|---|---|---|---|---|---|
| S01 | paraphrase | #1 | #1 | #1 | #1 |
| S02 | paraphrase | #1 | #2 ❌ | #1 | #3 ❌ |
| S03 | paraphrase | #5 | #3 | #10 ❌ | #5 |
| S04 | exact | #7 ❌ | #7 ❌ | #10 ❌ | #7 ❌ |
| S05 | paraphrase | #1 | #1 | #1 | #1 |
| S06 | neighbor | #1 | #1 | #1 | #1 |
| S07 | neighbor | #1 | #1 | #2 | #1 |
| S08 | paraphrase | #1 | #2 | #1 | - ❌ |
| S09 | paraphrase | #1 | #1 | #1 | #1 |
| S10 | paraphrase | #1 | #1 | #1 | #1 |
| S11 | exact | #1 | #1 | #1 | #1 |
| S12 | paraphrase | #1 | #1 | #1 | #4 |
| S13 | exact | #1 | #1 | #1 | #1 |

❌ = the generated answer did not pass (missing key facts or no cited source on an expected page).

**Notes**
- *Hit@k*: the first chunk on an expected page is within the top k. *MRR*: average of 1/rank.
- *Right doc @1* only requires the correct document, so it shows whether a method finds the document but not the page.
- Only hybrid + semantic can refuse (it is the only one with a reranker score), so the others score 0% on out-of-scope by design.
- Expected pages are anchor-based and can be narrower than every valid page, which understates scores for all methods equally.