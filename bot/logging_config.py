import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging():
    """Configure structured logging to both a log file and the console.

    - File handler (DEBUG): captures every API request, response payload, and
      traceback for post-mortem debugging.  Uses a plain formatter so that ANSI
      colour codes never pollute the log file.
    - Console handler (INFO): shows concise, human-readable messages during
      interactive use.
    """
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "trading_bot.log")

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers when the module is re-imported
    if logger.handlers:
        return logger

    # --- File handler (DEBUG) ------------------------------------------------
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s"
    )
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)

    # Strip ANSI escape codes from file output so logs stay machine-readable
    class _StripAnsiFilter(logging.Filter):
        """Remove ANSI colour codes before writing to the log file."""
        import re as _re
        _ansi_pattern = _re.compile(r"\x1b\[[0-9;]*m")

        def filter(self, record):
            if record.msg and isinstance(record.msg, str):
                record.msg = self._ansi_pattern.sub("", record.msg)
            return True

    file_handler.addFilter(_StripAnsiFilter())

    # --- Console handler (INFO) ----------------------------------------------
    console_fmt = logging.Formatter("%(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Module-level singleton
logger = setup_logging()
