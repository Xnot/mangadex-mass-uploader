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


def start_app(app: App):
    if hasattr(sys, "_MEIPASS"):
        resource_add_path(os.path.join(sys._MEIPASS))
    app.run()
