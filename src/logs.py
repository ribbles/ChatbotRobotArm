import logging

class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",   # Green
        "WARNING": "\033[93m", # Yellow
        "ERROR": "\033[91m",   # Red
        "CRITICAL": "\033[95m" # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        record.data = record.data if hasattr(record, 'data') else ""
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging():
    handler = logging.StreamHandler()
    formatter = ColorFormatter(
        "%(asctime)s.%(msecs)03d\t%(levelname)s\t%(name)s\t%(message)s\t%(data)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.handlers = [handler]
    logging.getLogger("connectionpool").setLevel(logging.DEBUG)
