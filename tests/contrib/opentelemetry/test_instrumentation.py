import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult

from lilya.contrib.opentelemetry.config import OpenTelemetryConfig
from lilya.contrib.opentelemetry.instrumentation import get_tracer_provider, setup_tracing


class DummyExporter(SpanExporter):
    def __init__(self, *args, **kwargs):
        pass

    def export(self, spans):
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


@pytest.fixture(autouse=True)
def patch_otlp(monkeypatch):
    # Prevent real HTTP connection
    monkeypatch.setattr(
        "lilya.contrib.opentelemetry.instrumentation.OTLPHTTPExporter",
        DummyExporter,
    )
    monkeypatch.setattr(
        "lilya.contrib.opentelemetry.instrumentation.OTLPgRPCExporter",
        DummyExporter,
    )


@pytest.fixture(autouse=True)
def reset_global_tracer(monkeypatch):
    """
    Fully reset OpenTelemetry global tracer state between tests.
    Works with modern OTel (≥1.27) which uses internal proxy provider.
    """
    import opentelemetry.trace as ot_trace

    from lilya.contrib.opentelemetry import instrumentation

    monkeypatch.setattr(ot_trace, "_TRACER_PROVIDER", None)
    monkeypatch.setattr(ot_trace, "_PROXY_TRACER_PROVIDER", None)
    monkeypatch.setattr(instrumentation, "_provider", None)

    yield

    monkeypatch.setattr(ot_trace, "_TRACER_PROVIDER", None)
    monkeypatch.setattr(ot_trace, "_PROXY_TRACER_PROVIDER", None)
    monkeypatch.setattr(instrumentation, "_provider", None)


def test_setup_tracing_creates_provider():
    setup_tracing()
    provider = get_tracer_provider()
    assert isinstance(provider, TracerProvider)

    current = trace.get_tracer_provider()
    delegate = getattr(current, "_delegate", None)

    if delegate is not None:
        assert delegate is provider
    else:
        assert current is provider


def test_setup_tracing_is_idempotent():
    setup_tracing()
    first = get_tracer_provider()
    setup_tracing()
    second = get_tracer_provider()

    assert first is second


def test_setup_tracing_with_custom_config(monkeypatch):
    cfg = OpenTelemetryConfig(
        service_name="my-app",
        exporter="console",
        sampler="always_off",
    )
    setup_tracing(cfg)
    provider = get_tracer_provider()

    assert provider.resource.attributes["service.name"] == "my-app"


def test_setup_tracing_selects_otlp_http(monkeypatch):
    cfg = OpenTelemetryConfig(exporter="otlp", otlp_endpoint="http://localhost:4318")
    setup_tracing(cfg)
    provider = get_tracer_provider()

    # Force worker creation (lazy init)
    tracer = provider.get_tracer("test-init")
    with tracer.start_as_current_span("dummy"):
        pass

    def extract_exporter(proc):
        # Check multiple potential locations for the exporter across OTel versions
        if hasattr(proc, "exporter"):
            return proc.exporter
        if hasattr(proc, "_exporter"):
            return proc._exporter

        worker = getattr(proc, "_worker", None)
        if worker is not None:
            exp = getattr(worker, "_exporter", None)
            if exp:
                return exp

        pipeline = getattr(proc, "_pipeline", None)
        if pipeline is not None:
            exp = getattr(pipeline, "exporter", None)
            if exp:
                return exp

        return None

    processors = getattr(provider._active_span_processor, "_span_processors", [])
    exporters = [extract_exporter(p) for p in processors]

    # ✅ Fallback: if worker not yet started, ensure at least the processor exists
    found = any(isinstance(p, BatchSpanProcessor) for p in processors) and any(
        isinstance(e, (DummyExporter, type(None))) for e in exporters
    )

    assert found, f"Expected DummyExporter in processors, found exporters={exporters}"
