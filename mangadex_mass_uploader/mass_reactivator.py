from kivy import Logger
from requests import HTTPError

from mangadex_mass_uploader.chapter_parser import Chapter, fetch_unavailable_chapters
from mangadex_mass_uploader.mangadex_api import MangaDexAPI
from mangadex_mass_uploader.utils import threaded, toggle_button, toggle_cancel
from mangadex_mass_uploader.widgets.app_screen import AppScreen
from mangadex_mass_uploader.widgets.chapter_info_input import ChapterInfoInput
from mangadex_mass_uploader.widgets.preview_output import PreviewOutput

logger = Logger


class ReactivationScreen(AppScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_chapters: list[Chapter] = []

    def clear_inputs(self):
        self.selected_chapters = []

    @threaded
    @toggle_button("update_preview_button")
    def update_preview(self):
        self.selected_chapters = fetch_unavailable_chapters(self.iter_info_inputs())
        preview_text = ""
        for chapter in self.selected_chapters:
            preview_text += str(chapter)
        if preview_text == "":
            preview_text = "No chapters selected."
        self.set_preview(preview_text)

    @threaded
    @toggle_cancel("mass_reactivate_button")
    def mass_reactivate(self):
        selected_chs = self.selected_chapters
        for idx, chapter in enumerate(selected_chs):
            if self.action_cancelled:
                logger.info(f"Another day, another disappointment")
                self.action_cancelled = False
                break
            logger.info(f"{idx + 1:>4}/{len(selected_chs):<4} - chapter reactivate: {chapter.id}")
            try:
                MangaDexAPI().reactivate_chapter(chapter.id)
            except HTTPError as exception:
                logger.error(f"{idx + 1:>4}/{len(selected_chs):<4} - {exception}")
        logger.info(f"Done")

    @threaded
    @toggle_cancel("mass_restore_button")
    def mass_restore(self):
        selected_chs = self.selected_chapters
        for idx, chapter in enumerate(selected_chs):
            if self.action_cancelled:
                logger.info(f"Another day, another disappointment")
                self.action_cancelled = False
                break
            logger.info(f"{idx + 1:>4}/{len(selected_chs):<4} - chapter restore: {chapter.id}")
            try:
                MangaDexAPI().restore_chapter(chapter.id)
            except HTTPError as exception:
                logger.error(f"{idx + 1:>4}/{len(selected_chs):<4} - {exception}")
        logger.info(f"Done")
