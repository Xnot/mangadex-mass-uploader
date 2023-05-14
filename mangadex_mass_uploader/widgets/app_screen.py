from contextlib import contextmanager

from kivy.clock import mainthread
from kivy.uix.screenmanager import Screen

from mangadex_mass_uploader.utils import toggle_button
from mangadex_mass_uploader.widgets.chapter_info_input import ChapterInfoInput


class AppScreen(Screen):
    @mainthread
    def set_preview(self, preview_text: str):
        self.ids["preview"].text = preview_text

    def iter_info_inputs(self):
        return filter(lambda item: isinstance(item[1], ChapterInfoInput), self.ids.items())

    def clear_inputs(self):
        pass

    @mainthread
    @toggle_button("clear_all_button")
    def clear_all_fields(self):
        for _, element in self.iter_info_inputs():
            element.text = ""
        self.clear_inputs()
        self.update_preview()
