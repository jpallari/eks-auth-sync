"""
Configure logging for the app
"""
import typing
import sys
import logging
import uuid
import structlog  # type: ignore

_PROCESSORS = (
    structlog.stdlib.filter_by_level,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
    structlog.threadlocal.merge_threadlocal,
)

_NOISY_LOG_SOURCES = (
    "boto",
    "urllib3",
    "s3transfer",
    "boto3",
    "botocore",
    "kubernetes",
)


def configure_logging(args: typing.Any) -> None:
    """
    Configure logging for the application.

    :param args: The CLI from `_args.parser.parse_args()`
    """
    # Configure processors
    processors = list(_PROCESSORS)
    if args.log_format.lower() == "json":
        processors.append(structlog.processors.JSONRenderer())
    elif args.log_format.lower() == "text":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        raise ValueError("Invalid log format: %s" % args.log_format)

    # Structlog configuration
    structlog.configure(
        processors=processors,
        context_class=dict,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Stdlib logging configuration
    logging.basicConfig(
        format="%(message)s", stream=sys.stderr, level=args.log_level.upper()
    )
    for source in _NOISY_LOG_SOURCES:
        logging.getLogger(source).setLevel(logging.CRITICAL)

    # Default bindings
    structlog.threadlocal.bind_threadlocal(
        cluster=args.cluster, run_id=str(uuid.uuid4()),
    )
