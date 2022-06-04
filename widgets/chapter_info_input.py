from kivy.uix.gridlayout import GridLayout


class ChapterInfoInput(GridLayout):
    @property
    def text(self):
        return self.ids["input"].text

    @text.setter
    def text(self, value: str):
        self.ids["input"].text = value
