import logging
import os
import threading
from itertools import zip_longest

from kivy.config import Config

Config.set("kivy", "desktop", 1)
Config.set("graphics", "window_state", "maximized")

from kivy.app import App
from kivy.clock import mainthread
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput
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
    def __init__(self, output_panel: TextInput):
        super().__init__()
        self.output_panel = output_panel

    @mainthread
    def emit(self, record: logging.LogRecord) -> None:
        self.output_panel.text += f"\n\n{self.format(record)}"


class LoginScreen(Screen):
    @threaded
    def login(self):
        self.toggle_login_button()
        try:
            self.manager.md_api.login(self.ids["username"].text, self.ids["password"].text)
        except HTTPError as exception:
            self.manager.logger.error(exception)
        else:
            self.set_uploader_screen()
        self.toggle_login_button()

    @mainthread
    def set_uploader_screen(self):
        self.manager.current = "mass_uploader_screen"

    @mainthread
    def toggle_login_button(self):
        self.ids["login_button"].disabled = not self.ids["login_button"].disabled


class ChapterTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # kinda cancer but ok
        self.bind(text=lambda *args: self.parent.parent.parent.update_preview())


class MassUploaderScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_files = []
        self.chapters = None

    @threaded
    def select_files(self):
        self.selected_files = filechooser.open_file(
            title="Chapter archives", multiple=True, filters=["*.zip", "*.cbz", "*"]
        )
        self.selected_files = natsorted(self.selected_files)
        self.update_preview()

    @threaded
    def parse_chapters(self):
        chapter_count = len(self.selected_files)
        if not chapter_count:
            return []
        chapters = {"file": self.selected_files}
        for field, element in self.ids.items():
            if not isinstance(element, ChapterTextInput):
                continue
            parsed_values = [value.strip() for value in element.text.split("\n")]
            # if one numerical chapter is inputted, the subsequent chapters are incremented by 1
            if len(parsed_values) == 1 and field == "chapter" and parsed_values[0].isdigit():
                parsed_values = range(int(parsed_values[0]), int(parsed_values[0]) + chapter_count)
                parsed_values = [str(value) for value in parsed_values]
            # for non-numerical chapter and other fields, single inputs are repeated
            elif len(parsed_values) == 1:
                parsed_values = parsed_values * chapter_count
            # get rid of invalid/extra inputs
            parsed_values = [None if value == "" else value for value in parsed_values]
            parsed_values = parsed_values[:chapter_count]
            chapters[field] = parsed_values
        # transpose into [{"file": 1, "chapter": 1}, {"file": 2, "chapter": 2}]
        chapter_dicts = []
        for chapter in zip_longest(*chapters.values()):
            ch_dict = {key: value for key, value in zip(chapters.keys(), chapter)}
            ch_dict["groups"] = [ch_dict.pop(f"group_{idx}_id") for idx in range(1, 6) if ch_dict[f"group_{idx}_id"]]
            ch_dict["chapter_draft"] = {
                "volume": ch_dict.pop("volume"),
                "chapter": ch_dict.pop("chapter"),
                "title": ch_dict.pop("title"),
                "translatedLanguage": ch_dict.pop("language"),
            }
            chapter_dicts.append(ch_dict)
        self.chapters = chapter_dicts

    @threaded
    def update_preview(self):
        self.parse_chapters()
        if len(self.chapters) == 0:
            self.ids["preview"].text = "No files selected."
            return
        preview_text = ""
        for chapter in self.chapters:
            preview_text += f"file: {os.path.basename(chapter['file'])}\n"
            for field in ["manga_id", "groups", "chapter_draft"]:
                preview_text += f"{field}: {chapter[field]}\n"
            preview_text += "\n"
        self.set_preview(preview_text)

    @mainthread
    def set_preview(self, preview_text: str):
        # scroll position is saved so that the preview doesn't jump around every time you type
        scroll_position = self.ids["preview"].scroll_y
        self.ids["preview"].text = preview_text
        # some math is done to prevent staying overscrolled when the amount of lines has decreased
        max_scroll = max(self.ids["preview"].minimum_height - self.ids["preview"].height, 0)
        self.ids["preview"].scroll_y = min(scroll_position, max_scroll)

    @threaded
    def mass_upload(self):
        self.toggle_upload_button()
        for idx, chapter in enumerate(self.chapters):
            self.manager.logger.info(f"Uploading chapter {idx + 1}/{len(self.chapters)}")
            try:
                self.manager.md_api.upload_chapter(chapter)
            except Exception as exception:
                self.manager.logger.error(exception)
                self.manager.logger.error(f"Could not upload chapter {idx + 1}/{len(self.chapters)}")
        self.manager.logger.info(f"Done")
        self.toggle_upload_button()

    @mainthread
    def toggle_upload_button(self):
        self.ids["mass_upload_button"].disabled = not self.ids["mass_upload_button"].disabled


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
        api_logger.setLevel("INFO")
        self.root.ids["manager"].logger = api_logger
        self.root.ids["manager"].md_api = MangaDexAPI()


if __name__ == "__main__":
    MassUploaderApp().run()
