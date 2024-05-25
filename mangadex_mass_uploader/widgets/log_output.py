import logging
import os
from datetime import datetime

from kivy.clock import mainthread
from kivy.config import Config
from kivy.uix.textinput import TextInput

from mangadex_mass_uploader.widgets.scrollbar_view import ScrollbarView


class LogOutput(ScrollbarView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)-7s | %(message)s\n", datefmt="%Y-%m-%dT%H:%M:%S"
        )
        panel_handler = APILogHandler(self, formatter)
        panel_handler.setLevel("INFO")
        file_handler = logging.FileHandler(
            f"{os.environ['KIVY_HOME']}/edit_logs/{datetime.now().strftime('%Y-%m-%dT%H_%M_%S')}.log"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel("DEBUG")
        api_logger = logging.getLogger("main")
        api_logger.addHandler(panel_handler)
        api_logger.addHandler(file_handler)
        api_logger.setLevel("DEBUG")


class APILogHandler(logging.Handler):
    def __init__(self, output_panel: LogOutput, formatter: logging.Formatter):
        super().__init__()
        self.output_panel = output_panel
        self.setFormatter(formatter)

    @mainthread
    def emit(self, record: logging.LogRecord) -> None:
        # truncate old logs
        old_text = self.output_panel.text.split("\n")
        old_text = "\n".join(old_text[-100:])
        self.output_panel.text = old_text + self.format(record)
