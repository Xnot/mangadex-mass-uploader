import logging

from kivy.clock import mainthread
from requests import HTTPError

from mangadex_mass_uploader.chapter_parser import Chapter, fetch_chapters, parse_edits
from mangadex_mass_uploader.mangadex_api import MangaDexAPI
from mangadex_mass_uploader.utils import threaded, toggle_button
from mangadex_mass_uploader.widgets.app_screen import AppScreen
from mangadex_mass_uploader.widgets.chapter_info_input import ReactiveInfoInput
from mangadex_mass_uploader.widgets.preview_output import PreviewOutput

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

logger = logging.getLogger("api_logger")


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
        self.selected_chapters = fetch_chapters(self.iter_info_inputs())
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

    @threaded
    def update_preview(self):
        self.edited_chapters = parse_edits(self.selected_chapters, self.iter_info_inputs())
        preview_text = ""
        for chapter in self.edited_chapters:
            preview_text += str(chapter)
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
                MangaDexAPI().edit_chapter(new_chapter.to_api())
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
                MangaDexAPI().delete_chapter(chapter.id)
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
                MangaDexAPI().deactivate_chapter(chapter.id)
            except HTTPError as exception:
                logger.error(exception)
                logger.error(f"Could not deactivate chapter {idx + 1}/{len(selected_chapters)}")
        logger.info(f"Done")
