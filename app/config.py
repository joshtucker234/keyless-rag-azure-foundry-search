"""All settings come from environment variables (see ../scripts/00-env.sh.example). Nothing is hard-coded and
nothing is a secret: every client authenticates with DefaultAzureCredential."""
import os


def _req(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Set {name} first (source scripts/00-env.sh and run `az login`).")
    return v


PROJECT_ENDPOINT = _req("PROJECT_ENDPOINT")  # https://<foundry>.services.ai.azure.com/api/projects/<project>
SEARCH_ENDPOINT = _req("SEARCH_ENDPOINT")  # https://<search>.search.windows.net
SEARCH_INDEX = os.getenv("SEARCH_INDEX", "idx-rag-lab-v2")
CHAT_DEPLOYMENT = os.getenv("CHAT_DEPLOYMENT", "chat")
SEMANTIC_CONFIG = "sem-config"
# Semantic reranker scores: answerable questions scored 2.5-3.4, unanswerable ~0.9-1.0 in our tests.
MIN_RERANKER_SCORE = float(os.getenv("MIN_RERANKER_SCORE", "2.0"))
# Optional. When empty, tracing is off. The string is an identifier, not a secret, when local auth is disabled.
APPINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
