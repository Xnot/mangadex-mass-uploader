import logging
import threading

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from natsort import natsorted
from plyer import filechooser
from requests import HTTPError

from mangadex_api import MangaDexAPI


def threaded(fun: callable) -> callable:
    def fun_threaded(*args, **kwargs):
        sub_thread = threading.Thread(target=fun, args=args, kwargs=kwargs)
        sub_thread.start()

    return fun_threaded


class APILogHandler(logging.Handler):
    def __init__(self, output_label: Label):
        super().__init__()
        self.output_label = output_label

    def emit(self, record: logging.LogRecord) -> None:
        self.output_label.text += f"\n\n{self.format(record)}"


class LoginScreen(Screen):
    @threaded
    def login(self):
        try:
            self.manager.md_api.login(self.ids["username"].text, self.ids["password"].text)
        except HTTPError as exception:
            self.manager.logger.error(exception)
        else:
            self.manager.current = "mass_uploader_screen"


class MassUploaderScreen(Screen):
    @threaded
    def select_files(self):
        self.selected_files = filechooser.open_file(
            title="Chapter archives", multiple=True, filters=["*.zip", "*.cbz", "*"]
        )
        self.selected_files = natsorted(self.selected_files)


class MassUploaderApp(App):
    def build(self):
        super().build()
        api_logger = logging.getLogger("api_logger")
        handler = APILogHandler(self.root.ids["log_output"])
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)-7s [%(module)s.%(funcName)s.%(lineno)s]\n%(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        api_logger.addHandler(handler)
        self.root.ids["manager"].logger = api_logger
        self.root.ids["manager"].md_api = MangaDexAPI()


if __name__ == "__main__":
    MassUploaderApp().run()
