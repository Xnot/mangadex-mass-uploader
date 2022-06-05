import logging
import os
from itertools import zip_longest

from kivy.config import Config

Config.set("kivy", "desktop", 1)
Config.set("graphics", "window_state", "maximized")

from kivy.app import App
from kivy.clock import mainthread, Clock
from kivy.uix.screenmanager import Screen
from natsort import natsorted
from plyer import filechooser
from requests import HTTPError

from mangadex_api import MangaDexAPI
from utils import start_app, threaded
from widgets.chapter_info_input import ChapterInfoInput
from widgets.log_output import LogOutput
from widgets.login_screen import LoginScreen


class EditorInfoInput(ChapterInfoInput):
    """
    ChapterInfoInput, but it updates the preview panel whenever the text changes.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # the event listener is scheduled to be bound at the first render
        # because kivy is dumb and can't access child nodes during init
        Clock.schedule_once(
            self.bind_preview_event,
            0
        )

    def bind_preview_event(self, dt=0):
        self.ids["input"].bind(
            text=lambda *args: App.get_running_app().root.ids["editor_screen"].update_preview()
        )


class SelectorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_chapters = []

    def fetch_chapters(self):
        chapters = {}
        for field_id, element in self.ids.items():
            if not isinstance(element, ChapterInfoInput):
                continue
            parsed_values = [value.strip() for value in element.text.split("\n")]
            # get rid of invalid inputs
            parsed_values = [None if value == "" else value for value in parsed_values]
            parsed_values = parsed_values[:chapter_count]
            chapters[field_id] = parsed_values
        # transpose into [{"file": 1, "chapter": 1}, {"file": 2, "chapter": 2}]
        chapter_dicts = []
        for chapter in zip_longest(*chapters.values()):
            ch_dict = {key: value for key, value in zip(chapters.keys(), chapter)}
            ch_dict["manga"] = ch_dict.pop("manga_id")
            ch_dict["groups"] = [ch_dict.pop(f"group_{idx}_id") for idx in range(1, 6) if ch_dict[f"group_{idx}_id"]]
            ch_dict["chapter_draft"] = {
                "volume": ch_dict.pop("volume"),
                "chapter": ch_dict.pop("chapter"),
                "title": ch_dict.pop("title"),
                "translatedLanguage": ch_dict.pop("language"),
            }
            chapter_dicts.append(ch_dict)
        self.selected_chapters = chapter_dicts

        self.manager.md_api.fetch(entity_id, filters)

    @threaded
    def update_preview(self):
        self.fetch_chapters()
        if len(self.selected_chapters) == 0:
            self.set_preview("No files selected.")
            return
        preview_text = ""
        for chapter in self.selected_chapters:
            preview_text += f"file: {os.path.basename(chapter['file'])}\n"
            for field in ["manga", "groups", "chapter_draft"]:
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
    def confirm_selection(self):
        self.toggle_upload_button()
        for idx, chapter in enumerate(self.selected_chapters):
            self.manager.logger.info(f"Uploading chapter {idx + 1}/{len(self.selected_chapters)}")
            try:
                self.manager.md_api.upload_chapter(chapter)
            except HTTPError as exception:
                self.manager.logger.error(exception)
                self.manager.logger.error(f"Could not upload chapter {idx + 1}/{len(self.selected_chapters)}")
        self.manager.logger.info(f"Done")
        self.toggle_upload_button()

    @mainthread
    def toggle_upload_button(self):
        self.ids["mass_upload_button"].disabled = not self.ids["mass_upload_button"].disabled

    @mainthread
    def clear_all_fields(self):
        for _, element in self.ids.items():
            if not isinstance(element, ChapterInfoInput):
                continue
            element.text = ""
        self.selected_chapters = []
        self.update_preview()


class EditorScreen(Screen):
    pass


class MassEditorApp(App):
    def build(self):
        super().build()
        self.icon = "mass_uploader.ico"
        self.root.ids["manager"].logger = logging.getLogger("api_logger")
        self.root.ids["manager"].md_api = MangaDexAPI()


if __name__ == "__main__":
    start_app(MassEditorApp())
