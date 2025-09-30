import logging


def setup_logging():
    """
    Configure logging for the entire project.
    This sets up two file handlers:
    - output.log: Contains INFO and DEBUG messages
    - error.log: Contains WARNING, ERROR, and CRITICAL messages
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any existing handlers to avoid duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    # Handler for normal output (INFO and below)
    output_handler = logging.FileHandler("output.log")
    output_handler.setLevel(logging.INFO)
    output_handler.setFormatter(formatter)
    output_handler.addFilter(lambda record: record.levelno <= logging.INFO)

    # Handler for errors (WARNING and above)
    error_handler = logging.FileHandler("error.log")
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)

    # Add handlers to root logger
    root_logger.addHandler(output_handler)
    root_logger.addHandler(error_handler)
