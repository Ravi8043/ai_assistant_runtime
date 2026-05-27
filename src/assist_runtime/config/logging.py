# shared/config/logging_config.py
import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logging(debug_mode: bool = False):
    """
    Centralized logging initialization.
    - Dev Mode: Detailed logs print directly to the terminal.
    - Prod Mode: Terminal stays clean; full logs are routed quietly to a file.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # Clear out any existing default handlers to avoid duplicate lines
    root_logger.handlers = []

    # Common format for our logs
    log_format = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s (Line: %(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if debug_mode:
        # --- DEVELOPMENT CONFIGURATION ---
        # Stream everything straight to the terminal screen
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_format)
        root_logger.addHandler(console_handler)
        
        logging.info("Logging initialized in [DEV MODE] - Outputting to console.")
    else:
        # --- PRODUCTION CONFIGURATION ---
        # 1. Silently stream everything into a background log file.
        # RotatingFileHandler keeps the file size safe (e.g., max 5MB, keeps 3 backups)
        file_handler = RotatingFileHandler("app.log", maxBytes=5_000_000, backupCount=3)
        file_handler.setFormatter(log_format)
        root_logger.addHandler(file_handler)
        
        # 2. Add a clean terminal handler that ONLY prints warnings/errors to the user
        clean_console = logging.StreamHandler(sys.stdout)
        clean_console.setLevel(logging.WARNING)  # Hides DEBUG and INFO from the user!
        clean_console.setFormatter(logging.Formatter("%(levelname)s: %(message)s")) # Cleaner format
        root_logger.addHandler(clean_console)