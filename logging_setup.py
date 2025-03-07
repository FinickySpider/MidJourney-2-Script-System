import logging

class LogHandler(logging.Handler):
    def __init__(self, log_viewer):
        super().__init__()
        self.log_viewer = log_viewer

    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelno
            if level >= logging.ERROR:
                tag = "error"
            elif level >= logging.WARNING:
                tag = "warning"
            elif level >= logging.INFO:
                tag = "info"
            else:
                tag = "neutral"
            self.log_viewer.add_log(msg, tag)
        except Exception:
            self.handleError(record)

def setup_logger(log_viewer):
    logger = logging.getLogger("Minerva")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    fh = logging.FileHandler("Session.log", encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    lh = LogHandler(log_viewer)
    lh.setFormatter(formatter)
    logger.addHandler(lh)
    return logger
