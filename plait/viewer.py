# -*- coding: utf-8 -*-

import urwid

def strip_host(host):
    if host.count(".") >= 2:
        host, _ = host.split(".", 1)
    return host


class ViewerContent(urwid.ListBox):
    def __init__(self):
        walker = urwid.SimpleListWalker([])
        super(ViewerContent, self).__init__(walker)

    def write(self, text):
        new_text = urwid.Text(text)
        self.body.append(new_text)
        try:
            self.body.set_focus(self.body.focus + 1)
        except: pass

class ViewerList(urwid.ListBox):
    def __init__(self, hosts):
        body = [urwid.Text("Hosts", align='center'), urwid.Divider(u"─")]
        for host in hosts:
            button = ViewerItem(host)
            body.append(button)
        walker = urwid.SimpleFocusListWalker(body)
        super(ViewerList, self).__init__(walker)


class ViewerDisplay(urwid.LineBox):
    def __init__(self, initial=urwid.SolidFill('-')):
        body = urwid.WidgetPlaceholder(initial)
        super(ViewerDisplay, self).__init__(
            body,
            tline=' ', bline=' ', rline=' ',
            trcorner=' ', brcorner=' ',
            tlcorner=u'│', blcorner=u'│')

    def show(self, button, item):
        self.original_widget.original_widget = item.content

class ViewerItemLabel(urwid.AttrMap):
    def __init__(self, label):
        self.button = urwid.Button(label)
        super(ViewerItem, self).__init__(self.button, 'button', focus_map='standout')

class ViewerItem(object):
    def __init__(self, label, widget):
        self.label = ViewerItemLabel(label)
        self.widget = widget

class VerticalViewer(urwid.LineBox):
    def __init__(self):
        stripped = map(strip_host, items)
        max_length = max(map(len, stripped)) + 4
        self.buttons = ViewerList(items)
        self.display = ViewerDisplay()
        self.body = urwid.Columns([(max_length, self.buttons), self.display])
        super(Viewer, self).__init__(self.body)
        self.connect_list()
        self.loop = None

    def connect_list(self):
        for item in self.items:
            if not isinstance(item, ViewerItem):
                continue
            urwid.connect_signal(item.original_widget, 'click', self.display.show, item)
        self.display.show(None, self.items[0])

    def keypress(self, size, key):
        retval = super(Viewer, self).keypress(size, key)
        focus = self.buttons.focus
        self.display.show(focus.button, focus)
        return retval

    def handle_keys(self, key):
        if key.lower() == 'q':
            self.loop = None
            raise urwid.ExitMainLoop()
        return key

    @property
    def items(self):
        return self.buttons.body[2:]

    def get_item(self, name):
        for item in self.items:
            if item.label == name:
                return item

    def write(self, name, text):
        item = self.get_item(name)
        item.attr_map = {None: 'ready'}
        item.focus_map = {None: 'ready_selected'}
        item.write(text)
        self.loop.draw_screen()

