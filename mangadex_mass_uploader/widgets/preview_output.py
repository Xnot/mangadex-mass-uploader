from mangadex_mass_uploader.widgets.scrollbar_view import ScrollbarView


class PreviewOutput(ScrollbarView):
    @property
    def text(self):
        return self.ids["preview_text"].text

    @text.setter
    def text(self, value: str):
        # scroll position is saved so that the preview doesn't jump around every time you type
        scroll_position = (1 - self.scroll_y) * (self.viewport_size[1] - self.height)
        self.ids["preview_text"].text = value
        # adjust scroll position to new viewport size
        scroll_position = 1 - scroll_position / (self.viewport_size[1] - self.height)
        self.scroll_y = min(max(scroll_position, 0), 1)
