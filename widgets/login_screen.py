from kivy.clock import mainthread
from kivy.uix.screenmanager import Screen
from requests import HTTPError

from utils import threaded


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
