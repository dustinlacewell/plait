import urwid

from plait.linebox import BorderBox, horizontalBorder


class Header(urwid.Columns):
    def __init__(self, title=""):
        super(Header, self).__init__([])
        self._title = urwid.Text(" " + title, align='left')
        self._text = urwid.Text("", align='right')
        self._update_contents()

    def _update_contents(self):
        self.contents = [
            (self._title, self.options(width_type='given',
                                       width_amount=len(self.title))),
            (self._text, self.options(width_type='weight')),
        ]

    @property
    def title(self):
        return self._title.get_text()[0]

    @title.setter
    def title(self, text):
        self._title.set_text(" " + text)
        self._update_contents()

    @property
    def text(self):
        return self._text.get_text()[0]

    @text.setter
    def text(self, text):
        self._text.set_text(text + " ")
        self._update_contents()

default_body = urwid.SolidFill(" ")

class ConsoleFrame(BorderBox):
    def __init__(self, title, body=default_body):
        self._frame = urwid.Frame(default_body, header=Header(title))
        super(ConsoleFrame, self).__init__(self._frame)
        self.show(body)

    def show(self, w, header_text=""):
        self._frame.contents['body'] = (BorderBox(w, **horizontalBorder()), None)
        self._frame._header.text = header_text
