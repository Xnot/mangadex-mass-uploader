from kivy.clock import mainthread
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen

from mangadex_mass_uploader.utils import toggle_button
from mangadex_mass_uploader.widgets.chapter_info_input import ChapterInfoInput, ReactiveInfoInput


class AppScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.action_cancelled: bool = False
        self._cancel_button: Button = Button(
            text="cancel",
            background_color="cc0000",
            on_release=lambda _: self.cancel_action(),
        )

    @mainthread
    def set_preview(self, preview_text: str):
        self.ids["preview"].text = preview_text

    def iter_info_inputs(self) -> filter:
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

    @mainthread
    def return_to_app_selection(self):
        self.manager.current = "app_selection_screen"

    def cancel_action(self):
        self.action_cancelled = True

    @mainthread
    def place_cancel_button(self, replaced_button: Button):
        idx = self.ids["buttons_container"].children.index(replaced_button)
        self.ids["buttons_container"].remove_widget(replaced_button)
        self.ids["buttons_container"].add_widget(self._cancel_button, idx)

    @mainthread
    def remove_cancel_button(self, replaced_button: Button):
        idx = self.ids["buttons_container"].children.index(self._cancel_button)
        self.ids["buttons_container"].remove_widget(self._cancel_button)
        self.ids["buttons_container"].add_widget(replaced_button, idx)
