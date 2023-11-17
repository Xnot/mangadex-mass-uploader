import logging
import os
from sys import argv

from kivy.clock import Clock, mainthread
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen
from requests import HTTPError

from mangadex_mass_uploader.mangadex_api import MangaDexAPI
from mangadex_mass_uploader.utils import threaded, toggle_button


class SavedLoginButton(Button):
    def __init__(self, login_screen, **kwargs):
        self.login_screen = login_screen
        super().__init__(**kwargs)

    def on_release(self):
        try:
            MangaDexAPI().load_login(self.text)
        except HTTPError as exception:
            logging.getLogger("api_logger").error(exception)
        else:
            self.login_screen.leave_login_screen()


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # the event listener is scheduled to be bound at the first render
        # because kivy is dumb and can't access child nodes during init
        Clock.schedule_once(self.append_saved_logins)

    def append_saved_logins(self, _):
        if not os.path.exists(".logins"):
            return
        for file in os.listdir(".logins"):
            self.ids["saved_login_container"].add_widget(SavedLoginButton(self, text=file[:-5]))

    @threaded
    @toggle_button("login_button")
    def login(self):
        try:
            if "bypass_login" not in argv:
                MangaDexAPI().login(
                    self.ids["username"].text,
                    self.ids["password"].text,
                    self.ids["client_id"].text,
                    self.ids["client_secret"].text,
                    self.ids["remember_me"].active,
                )
        except HTTPError as exception:
            logging.getLogger("api_logger").error(exception)
        else:
            self.leave_login_screen()

    @mainthread
    def leave_login_screen(self):
        self.manager.current = "app_selection_screen"
