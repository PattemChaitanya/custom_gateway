import logging
import os
import structlog


def configure_logging(level: str = "INFO"):
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper(), logging.INFO),
        force=True,
    )

    # Optional database log handler. Enabled only when explicitly requested to
    # avoid adding extra write latency to all requests by default.
    if os.getenv("ENABLE_DB_LOG_HANDLER", "false").lower() in ("1", "true", "yes"):
        try:
            from app.logging.db_handler import DatabaseLogHandler

            root_logger = logging.getLogger()
            has_db_handler = any(
                isinstance(handler, DatabaseLogHandler)
                for handler in root_logger.handlers
            )
            if not has_db_handler:
                db_handler = DatabaseLogHandler()
                db_handler.setLevel(
                    getattr(logging, level.upper(), logging.INFO))
                db_handler.setFormatter(logging.Formatter("%(message)s"))
                root_logger.addHandler(db_handler)
        except Exception:
            logging.getLogger(__name__).warning(
                "Failed to initialize DatabaseLogHandler", exc_info=True
            )

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__):
    return structlog.get_logger(name)
