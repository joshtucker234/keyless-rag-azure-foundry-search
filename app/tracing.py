"""OpenTelemetry tracing to Application Insights (keyless: exporter authenticates with Entra, not the ikey).

Import this before creating any SDK clients. Set TRACING=0 to turn it off. Needs the "Monitoring Metrics Publisher"
role on the App Insights resource for the signed-in identity.
"""
import os

from config import APPINSIGHTS_CONNECTION_STRING

ENABLED = os.environ.get("TRACING", "1") != "0" and bool(APPINSIGHTS_CONNECTION_STRING)

if ENABLED:
    os.environ.setdefault("OTEL_SERVICE_NAME", "keyless-rag-app")
    from azure.identity import DefaultAzureCredential
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(
        connection_string=APPINSIGHTS_CONNECTION_STRING,
        credential=DefaultAzureCredential(),
        enable_live_metrics=False,
    )

from opentelemetry import trace  # noqa: E402  (no-op tracer when not configured)

tracer = trace.get_tracer("keyless.rag")
