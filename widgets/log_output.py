import logging

from kivy.clock import mainthread
from kivy.uix.textinput import TextInput


class APILogHandler(logging.Handler):
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)-7s | %(message)s | [%(module)s.%(funcName)s.%(lineno)s]\n",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    def __init__(self, output_panel: TextInput):
        super().__init__()
        self.output_panel = output_panel

    @mainthread
    def emit(self, record: logging.LogRecord) -> None:
        self.output_panel.text += self.format(record)


class LogOutput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        handler = APILogHandler(self)
        api_logger = logging.getLogger("api_logger")
        api_logger.addHandler(handler)
        api_logger.setLevel("INFO")
