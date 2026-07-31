import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging and silence the leaky httpx request logger."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
