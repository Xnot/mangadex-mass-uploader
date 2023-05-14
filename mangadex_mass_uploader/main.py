import kivy_config

from kivy.app import App

from mangadex_mass_uploader.mass_editor import EditModificationScreen, EditSelectionScreen
from mangadex_mass_uploader.mass_uploader import UploaderScreen
from mangadex_mass_uploader.widgets.log_output import LogOutput
from mangadex_mass_uploader.widgets.login_screen import LoginScreen
from utils import start_app


class MainApp(App):
    def build(self):
        super().build()
        self.icon = "../assets/mass_uploader.ico"


def main():
    start_app(MainApp())


if __name__ == "__main__":
    main()
