#!/usr/bin/env bash
# Steps 1-3 of the lab: resource group, Foundry resource + project + model deployments, Search, Storage, RBAC.
# Prereq: `az login` to the tenant that owns the subscription, then `source scripts/00-env.sh`.
set -euo pipefail
: "${SUB:?source scripts/00-env.sh first}"
az account set --subscription "$SUB"
ME=$(az ad signed-in-user show --query id -o tsv)

echo "== resource group =="
az group create -n "$RG" -l "$LOC" --tags $TAGS -o none

echo "== Foundry resource (AIServices) =="
az cognitiveservices account create -g "$RG" -n "$FOUNDRY" -l "$LOC" --kind AIServices --sku S0 \
  --custom-domain "$FOUNDRY" --allow-project-management --tags $TAGS --yes -o none

echo "== Foundry project (REST, because the CLI has no --tags for projects and a tag policy may require them) =="
cat > /tmp/project.json <<JSON
{"location":"$LOC","identity":{"type":"SystemAssigned"},
 "tags":{"Owner":"$OWNER_EMAIL","Purpose":"rag-lab","project":"keyless-rag","environment":"sandbox"},
 "properties":{"displayName":"Keyless RAG lab","description":"Keyless RAG chat app"}}
JSON
az rest --method put -o none \
  --url "https://management.azure.com/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.CognitiveServices/accounts/$FOUNDRY/projects/$PROJECT?api-version=2025-06-01" \
  --body @/tmp/project.json

echo "== model deployments (chat + embedding) =="
az cognitiveservices account deployment create -g "$RG" -n "$FOUNDRY" --deployment-name chat \
  --model-name gpt-4.1-mini --model-version 2025-04-14 --model-format OpenAI --sku-name GlobalStandard --sku-capacity 50 -o none
az cognitiveservices account deployment create -g "$RG" -n "$FOUNDRY" --deployment-name embedding \
  --model-name text-embedding-3-small --model-version 1 --model-format OpenAI --sku-name GlobalStandard --sku-capacity 50 -o none

echo "== AI Search (Basic, Entra + key for now, system-assigned identity, free semantic ranker) =="
az search service create -g "$RG" -n "$SEARCH" -l "$SEARCH_LOC" --sku basic --partition-count 1 --replica-count 1 \
  --auth-options aadOrApiKey --aad-auth-failure-mode http401WithBearerChallenge --semantic-search free \
  --identity-type SystemAssigned --tags $TAGS -o none

echo "== Storage (Entra only: shared key disabled, no public blobs) =="
az storage account create -g "$RG" -n "$STORAGE" -l "$STORAGE_LOC" --sku Standard_LRS --kind StorageV2 \
  --allow-blob-public-access false --allow-shared-key-access false --min-tls-version TLS1_2 --tags $TAGS -o none

echo "== RBAC: you =="
FID=$(az cognitiveservices account show -g "$RG" -n "$FOUNDRY" --query id -o tsv)
SID=$(az search service show -g "$RG" -n "$SEARCH" --query id -o tsv)
STID=$(az storage account show -g "$RG" -n "$STORAGE" --query id -o tsv)
for pair in "Search Service Contributor|$SID" "Search Index Data Contributor|$SID" \
            "Cognitive Services OpenAI User|$FID" "Foundry User|$FID" "Storage Blob Data Contributor|$STID"; do
  az role assignment create --assignee-object-id "$ME" --assignee-principal-type User --role "${pair%%|*}" --scope "${pair##*|}" -o none
done

echo "== RBAC: the Search service's managed identity (this is what makes the indexer keyless) =="
MI=$(az search service show -g "$RG" -n "$SEARCH" --query identity.principalId -o tsv)
for pair in "Cognitive Services OpenAI User|$FID" "Cognitive Services User|$FID" "Storage Blob Data Reader|$STID"; do
  az role assignment create --assignee-object-id "$MI" --assignee-principal-type ServicePrincipal --role "${pair%%|*}" --scope "${pair##*|}" -o none
done
echo "Done. Role assignments can take a few minutes to take effect."
