#!/usr/bin/env bash
# Steps 2 and 4: create the index, data source, skillset and indexer from infra/search/*.template.json.
# Creating the indexer starts the first run. Layout costs about $10 per 1,000 pages: ~1,440 pages is ~$14.
set -euo pipefail
cd "$(dirname "$0")/.."
TOKEN=$(az account get-access-token --resource https://search.azure.com --query accessToken -o tsv)
render() {
  sed -e "s|__SEARCH_INDEX__|$SEARCH_INDEX|g" -e "s|__AOAI_ENDPOINT__|$AOAI_ENDPOINT|g" -e "s|__SKILLSET__|$SKILLSET|g" \
      -e "s|__DATASOURCE__|$DATASOURCE|g" -e "s|__INDEXER__|$INDEXER|g" -e "s|__STORAGE_RESOURCE_ID__|$STORAGE_RESOURCE_ID|g" "$1"
}
put() {  # put <path> <template>
  code=$(render "$2" | curl -s -o /tmp/out.json -w '%{http_code}' -X PUT "$SEARCH_ENDPOINT/$1?api-version=$API" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" --data @-)
  echo "$1 -> HTTP $code"
  [[ $code =~ ^2 ]] || { cat /tmp/out.json; exit 1; }
}
put "indexes/$SEARCH_INDEX"   infra/search/index.template.json
put "datasources/$DATASOURCE" infra/search/datasource.template.json
put "skillsets/$SKILLSET"     infra/search/skillset.template.json
put "indexers/$INDEXER"       infra/search/indexer.template.json
echo "Watch progress with scripts/04-indexer-status.sh. Do NOT delete or reset the indexer later: that re-bills every page."
