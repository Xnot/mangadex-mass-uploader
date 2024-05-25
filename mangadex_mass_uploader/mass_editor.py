import dataclasses
import logging
import os
import pickle
from datetime import datetime

from kivy.clock import mainthread
from plyer import filechooser
from requests import HTTPError

from mangadex_mass_uploader.chapter_parser import (
    Chapter,
    fetch_chapters,
    parse_edits,
    prepare_chapters_for_restore,
)
from mangadex_mass_uploader.mangadex_api import MangaDexAPI
from mangadex_mass_uploader.utils import threaded, toggle_button, toggle_cancel
from mangadex_mass_uploader.widgets.app_screen import AppScreen
from mangadex_mass_uploader.widgets.chapter_info_input import ReactiveInfoInput
from mangadex_mass_uploader.widgets.preview_output import PreviewOutput

logger = logging.getLogger("main")


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

    def restore_backup(self) -> None:
        self.choose_backup_file()
        self.prepare_restore()

    def choose_backup_file(self) -> None:
        backup_file = filechooser.open_file(
            title="Edit backups",
            filters=["*.pickle"],
            path=f"{os.environ['KIVY_HOME']}/edits/",
        )
        if not backup_file:
            self.selected_chapters = []
        with open(
            backup_file[0],
            "rb",
        ) as file:
            self.selected_chapters = pickle.load(file)["old"]

    @threaded
    def prepare_restore(self) -> None:
        restored_chapts, current_chapts = prepare_chapters_for_restore(self.selected_chapters)
        self.selected_chapters = current_chapts
        self.go_to_editor_and_reverse_fill(restored_chapts)

    @mainthread
    def go_to_editor_and_reverse_fill(self, restored_chapts: list[Chapter]) -> None:
        self.manager.current = "edit_modification_screen"
        self.manager.current_screen.selected_chapters = self.selected_chapters
        self.manager.current_screen.edited_chapters = restored_chapts
        self.manager.current_screen.reverse_fill_edit_fields()


class EditModificationScreen(AppScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_chapters: list[Chapter] = []
        self.edited_chapters: list[Chapter] = []

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

    @mainthread
    def reverse_fill_edit_fields(self):
        field_texts = {}
        for field_id, element in self.iter_info_inputs():
            field_texts[field_id] = ""
            for chapter in self.edited_chapters:
                value = getattr(chapter, field_id)
                if isinstance(value, list):
                    value = ",".join(value)
                if value is None:
                    value = ""
                field_texts[field_id] += value + "\n"
        # apply updates separately at the end to prevent update_preview triggers from interfering
        for field_id, element in self.iter_info_inputs():
            element.text = field_texts[field_id]

    @threaded
    @toggle_cancel("mass_edit_button")
    @toggle_button(["mass_delete_button", "mass_deactivate_button"])
    def mass_edit(self):
        selected_chs = self.selected_chapters
        edited_chs = self.edited_chapters

        # save edit to file
        with open(
            f"{os.environ['KIVY_HOME']}/edits/{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.pickle",
            "wb",
        ) as file:
            pickle.dump({"old": selected_chs, "new": edited_chs}, file)

        done = []
        skipped = []
        errored = []
        for idx, (old_chapter, new_chapter) in enumerate(zip(selected_chs, edited_chs)):
            old_ch: Chapter = dataclasses.replace(old_chapter)
            new_ch: Chapter = dataclasses.replace(new_chapter)
            if self.action_cancelled:
                logger.info(f"Another day, another disappointment")
                self.action_cancelled = False
                break
            try:
                if old_ch.manga_id != new_ch.manga_id:
                    logger.info(f"{idx + 1:>4}/{len(edited_chs):<4} - title move: {old_ch.id}")
                    MangaDexAPI().edit_chapter_manga(new_ch.id, new_ch.manga_id)
                    new_ch.version += 1
                    old_ch.version = new_ch.version
                    # update manga for last equality check
                    old_ch.manga_id = new_ch.manga_id
                if old_ch.uploader_id != new_ch.uploader_id:
                    logger.info(f"{idx + 1:>4}/{len(edited_chs):<4} - uploader move: {old_ch.id}")
                    MangaDexAPI().edit_chapter_uploader(new_ch.id, new_ch.uploader_id)
                    new_ch.version += 1
                    old_ch.version = new_ch.version
                    # update uploader for last equality check
                    old_ch.uploader_id = new_ch.uploader_id
                if old_ch != new_ch:
                    logger.info(f"{idx + 1:>4}/{len(edited_chs):<4} - chapter edit: {old_ch.id}")
                    MangaDexAPI().edit_chapter(new_ch.to_api())
                    new_ch.version += 1
                    old_ch.version = new_ch.version
            except HTTPError as exception:
                logger.error(f"{idx + 1:>4}/{len(edited_chs):<4} - {exception}")
                errored.append(old_ch.id)
            else:
                if old_chapter.version == old_ch.version:
                    skipped.append(old_ch.id)
                else:
                    done.append(old_ch.id)
        logger.info(f"Done: {len(done)}")
        logger.info(f"Skipped: {len(skipped)}")
        logger.info(f"Errored: {len(errored)}")
        logger.debug(f"Done: {done}")
        logger.debug(f"Skipped: {skipped}")
        logger.debug(f"Errored: {errored}")

    @threaded
    @toggle_cancel("mass_delete_button")
    @toggle_button(["mass_edit_button", "mass_deactivate_button"])
    def mass_delete(self):
        selected_chs = self.selected_chapters
        for idx, chapter in enumerate(selected_chs):
            if self.action_cancelled:
                logger.info(f"Another day, another disappointment")
                self.action_cancelled = False
                break
            logger.info(f"{idx + 1:>4}/{len(selected_chs):<4} - chapter delete: {chapter.id}")
            try:
                MangaDexAPI().delete_chapter(chapter.id)
            except HTTPError as exception:
                logger.error(f"{idx + 1:>4}/{len(selected_chs):<4} - {exception}")
        logger.info(f"Done")

    @threaded
    @toggle_cancel("mass_deactivate_button")
    @toggle_button(["mass_edit_button", "mass_delete_button"])
    def mass_deactivate(self):
        selected_chs = self.selected_chapters
        for idx, chapter in enumerate(selected_chs):
            if self.action_cancelled:
                logger.info(f"Another day, another disappointment")
                self.action_cancelled = False
                break
            logger.info(f"{idx + 1:>4}/{len(selected_chs):<4} - chapter deactivate: {chapter.id}")
            try:
                MangaDexAPI().deactivate_chapter(chapter.id)
            except HTTPError as exception:
                logger.error(f"{idx + 1:>4}/{len(selected_chs):<4} - {exception}")
        logger.info(f"Done")
