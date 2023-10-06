import logging
import os

from natsort import natsorted
from plyer import filechooser
from requests import HTTPError

from chapter_parser import Chapter, parse_upload_input
from mangadex_api import MangaDexAPI
from mangadex_mass_uploader.widgets.app_screen import AppScreen
from mangadex_mass_uploader.widgets.chapter_info_input import ReactiveInfoInput
from mangadex_mass_uploader.widgets.preview_output import PreviewOutput
from utils import threaded, toggle_button

logger = logging.getLogger("api_logger")


class UploaderInfoInput(ReactiveInfoInput):
    target_screen = "uploader_screen"


class UploaderScreen(AppScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_files = []
        self.chapters: list[Chapter] = []

    def clear_inputs(self):
        self.selected_files = []

    @threaded
    def select_files(self):
        self.selected_files = filechooser.open_file(
            title="Chapter archives", multiple=True, filters=["*.zip", "*.cbz", "*"]
        )
        self.selected_files = natsorted(self.selected_files)
        self.update_preview()

    @threaded
    def update_preview(self):
        self.chapters = parse_upload_input(self.iter_info_inputs(), self.selected_files)
        preview_text = ""
        for chapter in self.chapters:
            preview_text += str(chapter)
        if preview_text == "":
            preview_text = "No chapters selected."
        self.set_preview(preview_text)

    @threaded
    @toggle_button("mass_upload_button")
    def mass_upload(self):
        chapters = self.chapters.copy()
        for idx, chapter in enumerate(chapters):
            logger.info(f"Uploading chapter {idx + 1}/{len(chapters)}")
            try:
                MangaDexAPI().upload_chapter(chapter.to_api())
            except HTTPError as exception:
                logger.error(exception)
                logger.error(f"Could not upload chapter {idx + 1}/{len(chapters)}")
        logger.info(f"Done")
