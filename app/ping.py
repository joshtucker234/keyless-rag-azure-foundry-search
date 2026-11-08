"""Smoke test: keyless call to the chat deployment through the Foundry project SDK."""
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from config import CHAT_DEPLOYMENT, PROJECT_ENDPOINT

credential = DefaultAzureCredential()
project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)
client = project.get_openai_client()

resp = client.chat.completions.create(
    model=CHAT_DEPLOYMENT,
    messages=[{"role": "user", "content": "Reply with exactly: keyless auth works"}],
)
print(resp.choices[0].message.content)
print("tokens:", resp.usage.prompt_tokens, "in /", resp.usage.completion_tokens, "out")
