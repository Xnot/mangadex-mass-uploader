import logging
import os
from itertools import zip_longest
from typing import Union

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
from widgets.preview_output import PreviewOutput


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

    @staticmethod
    def parse_filter(value: str) -> Union[None, set[Union[None, str]]]:
        split_values = value.split("\n")
        if len(split_values) == 1 and split_values[0] == "":
            return None
        split_values = [None if value == "" else value for value in split_values]
        return set(split_values)

    def fetch_chapters(self):
        filters = {}
        for field_id, element in self.ids.items():
            if not isinstance(element, ChapterInfoInput):
                continue
            filters[field_id] = self.parse_filter(element.text)
        chapters = self.manager.md_api.get_chapter_list(filters)
        # flatten dicts
        chapter_dicts = []
        for chapter in chapters:
            manga = [relation["id"] for relation in chapter["relationships"] if relation["type"] == "manga"][0]
            groups = [relation["id"] for relation in chapter["relationships"] if relation["type"] == "scanlation_group"]
            ch_dict = {
                "id": chapter["id"],
                "manga": manga,
                "groups": groups,
                "volume": chapter["attributes"]["volume"],
                "chapter": chapter["attributes"]["chapter"],
                "title": chapter["attributes"]["title"],
                "translatedLanguage": chapter["attributes"]["translatedLanguage"],
                "version": chapter["attributes"]["version"],
            }
            chapter_dicts.append(ch_dict)
        self.selected_chapters = chapter_dicts

    @threaded
    def update_preview(self):
        self.toggle_button("update_preview_button")
        self.fetch_chapters()
        preview_text = ""
        for chapter in self.selected_chapters.copy():
            for field in ["id", "manga", "groups"]:
                preview_text += f"{field}: {chapter.pop(field)}\n"
            preview_text += f"{chapter}\n\n"
        if preview_text == "":
            preview_text = "No chapters selected."
        self.set_preview(preview_text)
        self.toggle_button("update_preview_button")

    @mainthread
    def set_preview(self, preview_text: str):
        self.ids["preview"].text = preview_text

    @mainthread
    def confirm_selection(self):
        self.manager.current = "editor_screen"
        self.manager.current_screen.selected_chapters = self.selected_chapters

    @mainthread
    def toggle_button(self, button_id: str):
        self.ids[button_id].disabled = not self.ids[button_id].disabled

    @mainthread
    def clear_all_fields(self):
        self.toggle_button("clear_all_button")
        for _, element in self.ids.items():
            if not isinstance(element, ChapterInfoInput):
                continue
            element.text = ""
        self.selected_chapters = []
        self.update_preview()
        self.toggle_button("clear_all_button")


class EditorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_chapters = []

    @mainthread
    def return_to_selector(self):
        self.manager.current = "selector_screen"


class MassEditorApp(App):
    def build(self):
        super().build()
        self.icon = "mass_uploader.ico"
        self.root.ids["manager"].logger = logging.getLogger("api_logger")
        self.root.ids["manager"].md_api = MangaDexAPI()


if __name__ == "__main__":
    start_app(MassEditorApp())
