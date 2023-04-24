from contextlib import contextmanager

from kivy.clock import mainthread
from kivy.uix.screenmanager import Screen

from mangadex_mass_uploader.widgets.chapter_info_input import ChapterInfoInput


class AppScreen(Screen):
    @contextmanager
    def toggle_button(self, button_id: str):
        self.ids[button_id].disabled = True
        yield
        self.ids[button_id].disabled = False

    @mainthread
    def set_preview(self, preview_text: str):
        self.ids["preview"].text = preview_text

    def iter_info_inputs(self):
        return filter(lambda item: isinstance(item[1], ChapterInfoInput), self.ids.items())

    def clear_inputs(self):
        pass

    @mainthread
    def clear_all_fields(self):
        with self.toggle_button("clear_all_button"):
            for _, element in self.iter_info_inputs():
                element.text = ""
            self.clear_inputs()
            self.update_preview()
