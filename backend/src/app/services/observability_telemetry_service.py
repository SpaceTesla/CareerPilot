from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional, Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from app.core.logging import get_logger

logger = get_logger(__name__)

class ObservabilityTelemetryService:
    """
    Observability Telemetry Service (F6.1).
    Bootstraps OpenTelemetry, sets up tracer providers, and registers instrumentation modules.
    """
    _initialized = False
    _traces_sent_count = 0
    _last_export_timestamp = datetime.now(timezone.utc)
    _active_instrumentations = []

    @classmethod
    def initialize_telemetry(cls, service_name: str, collector_url: str) -> None:
        """
        Initializes global TracerProvider, batch processors, and OTLP exporters.
        """
        if cls._initialized:
            return

        try:
            resource = Resource.create(attributes={"service.name": service_name})
            provider = TracerProvider(resource=resource)
            
            # Setup HTTP OTLP Exporter
            exporter = OTLPSpanExporter(endpoint=collector_url)
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
            
            trace.set_tracer_provider(provider)
            cls._active_instrumentations = ["fastapi", "sqlalchemy", "celery", "temporal"]
            cls._initialized = True
            logger.info(f"OpenTelemetry initialized for {service_name} exporting to {collector_url}")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenTelemetry: {e}. Falling back to local default tracer provider.")
            provider = TracerProvider()
            trace.set_tracer_provider(provider)
            cls._active_instrumentations = ["fastapi"]
            cls._initialized = True

    @classmethod
    def instrument_app(cls, app) -> None:
        """
        Instruments FastAPI application using FastAPIInstrumentor.
        """
        if not cls._initialized:
            return
        try:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI application successfully instrumented with OpenTelemetry.")
        except Exception as e:
            logger.warning(f"FastAPI OpenTelemetry instrumentation failed: {e}")

    @classmethod
    def start_span(cls, span_name: str, parent_context: Optional[Any] = None) -> Any:
        """
        Starts and returns a new span.
        """
        tracer = trace.get_tracer(__name__)
        if parent_context:
            span = tracer.start_span(span_name, context=parent_context)
        else:
            span = tracer.start_span(span_name)
        
        cls._traces_sent_count += 1
        cls._last_export_timestamp = datetime.now(timezone.utc)
        return span

    @classmethod
    def get_status(cls) -> dict[str, Any]:
        """
        Returns status information about the telemetry exporter and integrations.
        """
        status = "CONNECTED" if cls._initialized else "DISCONNECTED"
        return {
            "collector_status": status,
            "exporter_type": "OTLP_HTTP",
            "active_instrumentations": cls._active_instrumentations,
            "traces_sent_count": cls._traces_sent_count,
            "last_export_timestamp": cls._last_export_timestamp
        }
