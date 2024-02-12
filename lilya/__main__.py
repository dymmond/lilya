try:
    import click  # noqa
    import rich  # noqa
except ModuleNotFoundError:
    raise RuntimeError(
        "To use 'lilya cli' you need to install the dependencies. "
        "You can install them all by running 'pip install lilya[cli]'."
    ) from None
from lilya.cli.cli import lilya_cli


def run_cli() -> None:
    lilya_cli()


if __name__ == "__main__":  # pragma: no cover
    lilya_cli()
