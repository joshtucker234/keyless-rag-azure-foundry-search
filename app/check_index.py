"""Check indexer state and per-part page coverage in the v2 index."""
import collections
import json
import logging
import os
import subprocess
import urllib.request

from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)

tok = subprocess.run(
    "az account get-access-token --resource https://search.azure.com --query accessToken -o tsv",
    shell=True, capture_output=True, text=True,
).stdout.strip()
H = {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}
from config import SEARCH_ENDPOINT, SEARCH_INDEX

B = SEARCH_ENDPOINT
V = "api-version=2026-04-01"


def get(path):
    return json.load(urllib.request.urlopen(urllib.request.Request(f"{B}{path}?{V}", headers=H)))


def post(path, body):
    return json.load(urllib.request.urlopen(urllib.request.Request(f"{B}{path}?{V}", data=json.dumps(body).encode(), headers=H)))


st = get(f"/indexers/{os.environ['INDEXER']}/status")
lr = st["lastResult"]
print("indexer last run:", lr["status"], lr.get("startTime"), "->", lr.get("endTime"),
      "| processed", lr.get("itemsProcessed"), "failed", lr.get("itemsFailed"))
for h in st["executionHistory"][:3]:
    print("  hist:", h["status"], h.get("startTime"), h.get("itemsProcessed"), h.get("itemsFailed"))

rows, skip = [], 0
while True:
    r = post(f"/indexes/{SEARCH_INDEX}/docs/search",
             {"search": "*", "select": "title,page", "top": 1000, "skip": skip, "orderby": "chunk_id asc"})["value"]
    rows += r
    skip += 1000
    if len(r) < 1000:
        break
print("total chunks:", len(rows))

pages = collections.defaultdict(set)
for x in rows:
    pages[x["title"]].add(x["page"])

split_dir = os.path.join(os.path.dirname(__file__), "..", "pdfs-split")
bad, absent_total = [], 0
for f in sorted(os.listdir(split_dir)):
    n = len(PdfReader(os.path.join(split_dir, f)).pages)
    got = pages.get(f, set())
    missing = [p for p in range(1, n + 1) if p not in got]
    if missing:
        bad.append((f, n, len(got), missing))
        absent_total += len(missing)
print("parts with pages absent from the index:", len(bad), "| pages absent total:", absent_total)
for f, n, g, m in bad:
    print(f"  {f[:62]:62} {g}/{n} pages present; absent: {m[:12]}")
