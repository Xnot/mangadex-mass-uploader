import logging
from typing import Union

from kivy.config import Config

Config.set("kivy", "desktop", 1)
Config.set("graphics", "window_state", "maximized")

from kivy.app import App
from kivy.clock import mainthread
from requests import HTTPError

from mangadex_api import MangaDexAPI
from utils import start_app, threaded
from widgets.app_screen import AppScreen
from widgets.chapter_info_input import ReactiveInfoInput
from widgets.log_output import LogOutput
from widgets.login_screen import LoginScreen
from widgets.preview_output import PreviewOutput


class EditorInfoInput(ReactiveInfoInput):
    target_screen = "editor_screen"


class SelectorScreen(AppScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_chapters = []

    def clear_inputs(self):
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
        for field_id, element in self.iter_info_inputs():
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
        with self.toggle_button("update_preview_button"):
            self.fetch_chapters()
            preview_text = ""
            for chapter in self.selected_chapters:
                chapter = chapter.copy()
                for field in ["id", "manga", "groups"]:
                    preview_text += f"{field}: {chapter.pop(field)}\n"
                preview_text += f"{chapter}\n\n"
            if preview_text == "":
                preview_text = "No chapters selected."
            self.set_preview(preview_text)

    @mainthread
    def confirm_selection(self):
        self.fetch_chapters()
        self.manager.current = "editor_screen"
        self.manager.current_screen.selected_chapters = self.selected_chapters
        self.manager.current_screen.update_preview()


class EditorScreen(AppScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_chapters = []
        self.edited_chapters = []

    def clear_inputs(self):
        self.edited_chapters = []

    @mainthread
    def return_to_selector(self):
        self.manager.current = "selector_screen"

    def parse_edits(self):
        chapter_count = len(self.selected_chapters)
        edited_values = {}
        for field_id, element in self.iter_info_inputs():
            parsed_values = element.text.split("\n")
            # groups are comma-separated
            if field_id == "groups":
                parsed_values = [value.split(",") for value in parsed_values]
            # single inputs are repeated
            if len(parsed_values) == 1:
                parsed_values = parsed_values * chapter_count
            # pad inputs to chapter_count
            parsed_values += [""] * (chapter_count - len(parsed_values))
            edited_values[field_id] = parsed_values
        self.edited_chapters = []
        for chapter in self.selected_chapters:
            chapter = chapter.copy()
            for field in edited_values:
                new_value = edited_values[field].pop(0)
                if new_value == " ":
                    new_value = None
                if new_value not in ["", [""]]:
                    chapter[field] = new_value
            self.edited_chapters.append(chapter)

    @threaded
    def update_preview(self):
        self.parse_edits()
        preview_text = ""
        for chapter in self.edited_chapters:
            chapter = chapter.copy()
            for field in ["id", "manga", "groups"]:
                preview_text += f"{field}: {chapter.pop(field)}\n"
            preview_text += f"{chapter}\n\n"
        if preview_text == "":
            preview_text = "No chapters selected."
        self.set_preview(preview_text)

    @threaded
    def mass_edit(self):
        with self.toggle_button("mass_edit_button"):
            for idx, (old_chapter, new_chapter) in enumerate(zip(self.selected_chapters, self.edited_chapters)):
                if old_chapter == new_chapter:
                    self.manager.logger.info(f"Skipping unchanged chapter {idx + 1}/{len(self.edited_chapters)}")
                    continue
                self.manager.logger.info(f"Editing chapter {idx + 1}/{len(self.edited_chapters)}")
                try:
                    self.manager.md_api.edit_chapter(new_chapter.copy())
                except HTTPError as exception:
                    self.manager.logger.error(exception)
                    self.manager.logger.error(f"Could not upload chapter {idx + 1}/{len(self.edited_chapters)}")
            self.manager.logger.info(f"Done")


class MassEditorApp(App):
    def build(self):
        super().build()
        self.icon = "mass_uploader.ico"
        self.root.ids["manager"].logger = logging.getLogger("api_logger")
        self.root.ids["manager"].md_api = MangaDexAPI()


if __name__ == "__main__":
    start_app(MassEditorApp())
