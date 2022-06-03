import logging
import threading

from kivy.clock import mainthread
from kivy.uix.textinput import TextInput


def threaded(fun: callable) -> callable:
    def fun_threaded(*args, **kwargs):
        sub_thread = threading.Thread(target=fun, args=args, kwargs=kwargs)
        sub_thread.start()

    return fun_threaded


class APILogHandler(logging.Handler):
    def __init__(self, output_panel: TextInput):
        super().__init__()
        self.output_panel = output_panel

    @mainthread
    def emit(self, record: logging.LogRecord) -> None:
        self.output_panel.text += self.format(record)


def initialize_api_logger(output_panel: TextInput):
    api_logger = logging.getLogger("api_logger")
    handler = APILogHandler(output_panel)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)-7s | %(message)s | [%(module)s.%(funcName)s.%(lineno)s]\n",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    api_logger.addHandler(handler)
    api_logger.setLevel("INFO")
    return api_logger
