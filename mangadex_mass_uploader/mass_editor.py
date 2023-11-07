import re

from kivy import Logger
from kivy.clock import mainthread
from requests import HTTPError

from chapter_parser import Chapter, fetch_chapters
from mangadex_api import MangaDexAPI
from utils import threaded, toggle_button
from widgets.app_screen import AppScreen
from widgets.chapter_info_input import ReactiveInfoInput
from widgets.preview_output import PreviewOutput

# TODO update spec and throw in py build script
# TODO add usage section to readme
# TODO add min height to scroll bars?
# TODO text scaling
# TODO not fullscreen?
# TODO edit manga & uploader fields
# TODO add debug flag for prefills
# TODO pipeline with auto build and release
# TODO add discord hook or bot to auto-post releases
# TODO improved logging thing with revert logic
# TODO upload session checking probably broke
# TODO confirmation dialog for delete/disable and cancel button
# TODO multi group edit is not the same as V3 mass editor

logger = Logger


class EditorInfoInput(ReactiveInfoInput):
    target_screen = "edit_modification_screen"


class EditSelectionScreen(AppScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_chapters: list[Chapter] = []

    def clear_inputs(self):
        self.selected_chapters = []

    @threaded
    @toggle_button("update_preview_button")
    def update_preview(self):
        self.selected_chapters = fetch_chapters(self.iter_info_inputs())
        preview_text = ""
        for chapter in self.selected_chapters:
            preview_text += str(chapter)
        if preview_text == "":
            preview_text = "No chapters selected."
        self.set_preview(preview_text)

    @threaded
    def confirm_selection(self):
        self.fetch_chapters()
        self.go_to_editor()

    @mainthread
    def go_to_editor(self):
        self.manager.current = "edit_modification_screen"
        self.manager.current_screen.selected_chapters = self.selected_chapters
        self.manager.current_screen.update_preview()


class EditModificationScreen(AppScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_chapters = []
        self.edited_chapters = []

    def clear_inputs(self):
        self.edited_chapters = []

    @mainthread
    def return_to_selector(self):
        self.manager.current = "edit_selection_screen"

    def parse_edits(self):
        chapter_count = len(self.selected_chapters)
        edited_values = {}
        for field_id, element in self.iter_info_inputs():
            parsed_values: list[str | list[str]] | dict[str, list[list[str]]] = element.text.split(
                "\n"
            )
            # groups are comma-separated
            if field_id == "groups":
                parsed_values = [value.split(",") for value in parsed_values]
            # volume can have conditional inputs
            if field_id == "volume":
                parsed_values = [value.split(":") for value in parsed_values]
                sequential_inputs = [value[0] for value in parsed_values if len(value) == 1]
                conditional_inputs = [value for value in parsed_values if len(value) == 2]
                parsed_values = {
                    "sequential": sequential_inputs,
                    "conditional": conditional_inputs,
                }
                if len(parsed_values["sequential"]) == 1:
                    parsed_values["sequential"] = parsed_values["sequential"] * chapter_count
                parsed_values["sequential"] += [""] * (
                    chapter_count - len(parsed_values["sequential"])
                )
            # single inputs are repeated
            if isinstance(parsed_values, list) and len(parsed_values) == 1:
                parsed_values = parsed_values * chapter_count
            # pad inputs to chapter_count
            if isinstance(parsed_values, list):
                parsed_values += [""] * (chapter_count - len(parsed_values))
            edited_values[field_id] = parsed_values
        self.edited_chapters = []
        for chapter in self.selected_chapters:
            chapter = chapter.copy()
            for field in edited_values:
                field_values = edited_values[field]
                if isinstance(field_values, dict):
                    # apply conditionals first
                    for new_value, condition in field_values["conditional"]:
                        # empty inputs are ignored
                        if new_value in ["", [""]]:
                            continue
                        # space is used to set field to null
                        if new_value in [" ", [" "]]:
                            new_value = None
                        # condition can be a chapter or range
                        if re.match(r"\s*[0-9]+(\.[0-9]+)?\s*-\s*[0-9]+(\.[0-9]+)?\s*", condition):
                            start, end = sorted(
                                float(endpoint) for endpoint in condition.split("-")
                            )
                            if EditSelectionScreen.is_in_range(start, end, chapter["chapter"]):
                                chapter[field] = new_value
                        elif condition.strip() == chapter["chapter"]:
                            chapter[field] = new_value
                    field_values = field_values["sequential"]
                new_value = field_values.pop(0)
                # empty inputs are ignored
                if new_value in ["", [""]]:
                    continue
                # space is used to set field to null
                if new_value in [" ", [" "]]:
                    new_value = None
                # strip whitespace
                elif isinstance(new_value, list):
                    new_value = [value.strip() for value in new_value]
                else:
                    new_value = new_value.strip()
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
    @toggle_button(["mass_edit_button", "mass_delete_button", "mass_deactivate_button"])
    def mass_edit(self):
        selected_chapters = self.selected_chapters.copy()
        edited_chapters = self.edited_chapters.copy()
        for idx, (old_chapter, new_chapter) in enumerate(zip(selected_chapters, edited_chapters)):
            if old_chapter == new_chapter:
                continue
            logger.info(f"Editing chapter {idx + 1}/{len(edited_chapters)}")
            try:
                MangaDexAPI().edit_chapter(new_chapter.copy())
            except HTTPError as exception:
                logger.error(exception)
                logger.error(f"Could not edit chapter {idx + 1}/{len(edited_chapters)}")
        logger.info(f"Done")

    @threaded
    @toggle_button(["mass_edit_button", "mass_delete_button", "mass_deactivate_button"])
    def mass_delete(self):
        selected_chapters = self.selected_chapters.copy()
        for idx, chapter in enumerate(selected_chapters):
            logger.info(f"Deleting chapter {idx + 1}/{len(selected_chapters)}")
            try:
                MangaDexAPI().delete_chapter(chapter["id"])
            except HTTPError as exception:
                logger.error(exception)
                logger.error(f"Could not delete chapter {idx + 1}/{len(selected_chapters)}")
        logger.info(f"Done")

    @threaded
    @toggle_button(["mass_edit_button", "mass_delete_button", "mass_deactivate_button"])
    def mass_deactivate(self):
        selected_chapters = self.selected_chapters.copy()
        for idx, chapter in enumerate(selected_chapters):
            logger.info(f"Deactivating chapter {idx + 1}/{len(selected_chapters)}")
            try:
                MangaDexAPI().deactivate_chapter(chapter["id"])
            except HTTPError as exception:
                logger.error(exception)
                logger.error(f"Could not deactivate chapter {idx + 1}/{len(selected_chapters)}")
        logger.info(f"Done")
