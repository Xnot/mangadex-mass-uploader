import os
import sys
import logging
import threading

from kivy.app import App
from kivy.clock import mainthread
from kivy.resources import resource_add_path
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import Screen
from requests import HTTPError


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


class LoginScreen(Screen):
    @threaded
    def login(self):
        self.toggle_login_button()
        try:
            self.manager.md_api.login(self.ids["username"].text, self.ids["password"].text)
        except HTTPError as exception:
            self.manager.logger.error(exception)
        else:
            self.leave_login_screen()
        self.toggle_login_button()

    @mainthread
    def leave_login_screen(self):
        self.manager.current = self.screen_after_login

    @mainthread
    def toggle_login_button(self):
        self.ids["login_button"].disabled = not self.ids["login_button"].disabled


def start_app(app: App):
    if hasattr(sys, "_MEIPASS"):
        resource_add_path(os.path.join(sys._MEIPASS))
    app.run()
