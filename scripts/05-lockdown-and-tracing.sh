#!/usr/bin/env bash
# Steps 7 and 9: turn off key auth everywhere, create Application Insights, grant yourself ingestion rights.
# Run this AFTER the indexer has finished and the app works.
set -euo pipefail
echo "== disable key auth: Foundry and Search (shared key on Storage was disabled at creation) =="
FID=$(az cognitiveservices account show -g "$RG" -n "$FOUNDRY" --query id -o tsv)
az resource update --ids "$FID" --set properties.disableLocalAuth=true -o none
az search service update -g "$RG" -n "$SEARCH" --disable-local-auth true -o none

echo "== Log Analytics + workspace-based Application Insights (Entra-only ingestion) =="
az monitor log-analytics workspace create -g "$RG" -n "$LAW" -l "$LOC" --tags $TAGS -o none
LAWID=$(az monitor log-analytics workspace show -g "$RG" -n "$LAW" --query id -o tsv)
cat > /tmp/appi.json <<JSON
{"location":"$LOC","kind":"web",
 "tags":{"Owner":"$OWNER_EMAIL","Purpose":"rag-lab","environment":"sandbox"},
 "properties":{"Application_Type":"web","WorkspaceResourceId":"$LAWID","DisableLocalAuth":true}}
JSON
APPI_ID="/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.Insights/components/$APPI"
az rest --method PUT -o none --body @/tmp/appi.json --url "https://management.azure.com$APPI_ID?api-version=2020-02-02"
az role assignment create --assignee-object-id "$(az ad signed-in-user show --query id -o tsv)" --assignee-principal-type User \
  --role "Monitoring Metrics Publisher" --scope "$APPI_ID" -o none
CS=$(az rest --method GET --url "https://management.azure.com$APPI_ID?api-version=2020-02-02" --query properties.ConnectionString -o tsv)
echo
echo "Add this to your shell (an identifier, not a secret, because key ingestion is disabled):"
echo "export APPLICATIONINSIGHTS_CONNECTION_STRING='$CS'"
