import logging
import os
from itertools import zip_longest

from natsort import natsorted
from plyer import filechooser
from requests import HTTPError

from chapter_parser import Chapter, parse_upload_input
from mangadex_api import MangaDexAPI
from utils import threaded, toggle_button
from widgets.app_screen import AppScreen
from widgets.chapter_info_input import ReactiveInfoInput
from widgets.preview_output import PreviewOutput

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
            preview_text += f"file: {os.path.basename(str(chapter['file']))}\n"
            for field in ["manga", "groups", "chapter_draft"]:
                preview_text += f"{field}: {chapter[field]}\n"
            preview_text += "\n"
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
                MangaDexAPI().upload_chapter(chapter)
            except HTTPError as exception:
                logger.error(exception)
                logger.error(f"Could not upload chapter {idx + 1}/{len(chapters)}")
        logger.info(f"Done")
