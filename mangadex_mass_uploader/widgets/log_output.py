import logging

from kivy.clock import mainthread
from kivy.uix.textinput import TextInput

from mangadex_mass_uploader.widgets.scrollbar_view import ScrollbarView


class LogOutput(ScrollbarView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        handler = APILogHandler(self)
        api_logger = logging.getLogger("api_logger")
        api_logger.addHandler(handler)
        api_logger.setLevel("INFO")


class APILogHandler(logging.Handler):
    def __init__(self, output_panel: LogOutput):
        super().__init__()
        self.output_panel = output_panel
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(levelname)-7s | %(message)s\n", datefmt="%Y-%m-%dT%H:%M:%S"
            )
        )

    @mainthread
    def emit(self, record: logging.LogRecord) -> None:
        self.output_panel.text += self.format(record)
