#!/usr/bin/env bash
# Show indexer progress and chunk count. Runs can sit at "inProgress" with no new chunks for a long time, then resume.
set -euo pipefail
TOKEN=$(az account get-access-token --resource https://search.azure.com --query accessToken -o tsv)
curl -s "$SEARCH_ENDPOINT/indexers/$INDEXER/status?api-version=$API" -H "Authorization: Bearer $TOKEN" |
  python -c "import json,sys; d=json.load(sys.stdin); l=d.get('lastResult') or {}; print('status:',d['status'],'| last run:',l.get('status'),'| items',l.get('itemsProcessed'),'| failed',l.get('itemsFailed'))"
curl -s "$SEARCH_ENDPOINT/indexes/$SEARCH_INDEX/stats?api-version=$API" -H "Authorization: Bearer $TOKEN"
echo
