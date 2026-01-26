"""
Logging configuration for SC2 extraction system
"""
import logging
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[2]

def setup_logging(level: str = "DEBUG", log_file: str = None, console_output: bool = True):
    """
    Configure logging for the extraction system

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file (optional)
        console_output: Whether to output to console
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers = []

    # Suppress noisy sc2reader logging
    logging.getLogger('sc2reader').setLevel(logging.CRITICAL)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)-8s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Create Log File if not passed
    if not log_file:
        log_file = ROOT_DIR / "logs" / "replay_extraction.log"

    # File handler
    if log_file:
        # Create log directory if needed
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
