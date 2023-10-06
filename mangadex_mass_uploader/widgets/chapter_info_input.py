from kivy.app import App
from kivy.clock import Clock
from kivy.uix.gridlayout import GridLayout


class ChapterInfoInput(GridLayout):
    @property
    def text(self):
        return self.ids["input"].text

    @text.setter
    def text(self, value: str):
        self.ids["input"].text = value


class ReactiveInfoInput(ChapterInfoInput):
    """
    ChapterInfoInput, but it updates the preview panel whenever the text changes.
    """

    target_screen = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # the event listener is scheduled to be bound at the first render
        # because kivy is dumb and can't access child nodes during init
        Clock.schedule_once(self.bind_preview_event)

    def bind_preview_event(self, dt=0):
        self.ids["input"].bind(
            text=lambda *args: App.get_running_app()
            .root.ids["manager"]
            .get_screen(self.target_screen)
            .update_preview()
        )
