from opentelemetry import trace
from opentelemetry.util._once import Once


def reset_opentelemetry_globals():
    """
    Completely reset OpenTelemetry global tracer state between tests.
    """
    # Reset the global provider and "set-once" guard safely.
    if hasattr(trace, "_TRACER_PROVIDER"):
        trace._TRACER_PROVIDER = None

    # Reinitialize the Once guard used internally by OTel
    if hasattr(trace, "_TRACER_PROVIDER_SET_ONCE"):
        trace._TRACER_PROVIDER_SET_ONCE = Once()

    # Some OTel versions also use _PROVIDER_SET_ONCE (alias)
    if hasattr(trace, "_PROVIDER_SET_ONCE"):
        trace._PROVIDER_SET_ONCE = False
