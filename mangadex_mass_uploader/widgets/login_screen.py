import logging
from sys import argv

from kivy.clock import mainthread
from kivy.uix.screenmanager import Screen
from requests import HTTPError

from mangadex_mass_uploader.mangadex_api import MangaDexAPI
from mangadex_mass_uploader.utils import threaded, toggle_button


class LoginScreen(Screen):
    @threaded
    @toggle_button("login_button")
    def login(self):
        try:
            if "bypass_login" not in argv:
                MangaDexAPI().login(self.ids["username"].text, self.ids["password"].text)
        except HTTPError as exception:
            logging.getLogger("api_logger").error(exception)
        else:
            self.leave_login_screen()

    @mainthread
    def leave_login_screen(self):
        self.manager.current = self.screen_after_login
