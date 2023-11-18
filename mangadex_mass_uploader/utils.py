import os
import sys
import threading

from kivy.app import App
from kivy.resources import resource_add_path


def threaded(fun: callable) -> callable:
    def fun_threaded(*args, **kwargs):
        sub_thread = threading.Thread(target=fun, args=args, kwargs=kwargs)
        sub_thread.start()

    return fun_threaded


def toggle_button(button_ids: str | list[str]) -> callable:
    if isinstance(button_ids, str):
        button_ids = [button_ids]

    def button_toggle_decorator(method: callable) -> callable:
        def decorated_method(self, *args, **kwargs):
            for button_id in button_ids:
                self.ids[button_id].disabled = True
            try:
                method(self, *args, **kwargs)
            finally:
                for button_id in button_ids:
                    self.ids[button_id].disabled = False

        return decorated_method

    return button_toggle_decorator


def toggle_cancel(button_id: str) -> callable:
    def cancel_toggle_decorator(method: callable) -> callable:
        def decorated_method(self, *args, **kwargs):
            button = self.ids[button_id].__self__
            self.place_cancel_button(button)
            try:
                method(self, *args, **kwargs)
            finally:
                self.remove_cancel_button(button)

        return decorated_method

    return cancel_toggle_decorator


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
