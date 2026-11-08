#!/usr/bin/env bash
# Step 3: split the PDFs into <=30-page parts and upload them to Blob storage (Entra auth, no keys).
# Prereq: PDFs are in ./pdfs (see docs/pdf-list.md), `pip install pypdf`, `source scripts/00-env.sh`.
set -euo pipefail
python scripts/split_pdfs.py pdfs pdfs-split
az storage container create --account-name "$STORAGE" --name pdfs-split --auth-mode login -o none
az storage blob upload-batch --account-name "$STORAGE" --destination pdfs-split --source pdfs-split \
  --pattern "*.pdf" --auth-mode login --overwrite --no-progress -o none
echo -n "blobs uploaded: "
az storage blob list --account-name "$STORAGE" -c pdfs-split --auth-mode login --query "length(@)" -o tsv
