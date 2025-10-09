from lilya.contrib.opentelemetry.config import OpenTelemetryConfig


def test_config_defaults():
    cfg = OpenTelemetryConfig()

    assert cfg.service_name == "lilya-service"
    assert cfg.exporter in {"console", "otlp"}
    assert cfg.otlp_endpoint.startswith("http://")
    assert cfg.otlp_insecure is True
    assert cfg.sampler == "parentbased_always_on"


def test_config_override():
    cfg = OpenTelemetryConfig(
        service_name="custom-service",
        exporter="otlp",
        otlp_endpoint="http://collector:4318",
        otlp_insecure=False,
        sampler="always_off",
    )
    assert cfg.service_name == "custom-service"
    assert cfg.exporter == "otlp"
    assert cfg.otlp_endpoint == "http://collector:4318"
    assert cfg.otlp_insecure is False
    assert cfg.sampler == "always_off"
