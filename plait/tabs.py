import urwid

from blinker import signal

from plait.linebox import *

def h(v):
    '''clip an integer to 0-16 and return as hex digit character'''
    return hex(max(0, min(15, v)))[-1]

class TabDisplay(urwid.WidgetPlaceholder):
    """
    Simple placeholder for the current Tab's content.
    """
    def __init__(self, initial=urwid.SolidFill(' ')):
        super(TabDisplay, self).__init__(initial)

    def show(self, tab):
        self.original_widget = tab.content

class VerticalTabList(urwid.ListBox):
    """
    A ListBox for storing tabs.
    """

    def __init__(self):
        walker = urwid.SimpleFocusListWalker([])
        super(VerticalTabList, self).__init__(walker)

    def append(self, tab):
        self.body.append(tab)

    def insert(self, pos, tab):
        self.body.insert(pos, tab)

class Tab(urwid.AttrMap):
    """
    A Button that also tracks some other Widget for display in a VerticalTabs widget.
    """
    def __init__(self, label, content=urwid.SolidFill(' '), color=(8,8,0)):
        self.label = urwid.Button(label)
        self.content = content
        super(Tab, self).__init__(self.label, 'normal', focus_map='reversed')
        urwid.connect_signal(self.label, 'click', self.send)
        self.set_color(*color) # default color

    def send(self, sender):
        """
        Emit signal that the tab is currently selected.
        """
        signal('tab_click').send(self)

    def set_color(self, r, g, b):
        """
        Set the tab's attr and focus map from an RGB triplet. Focus is generated as
        a slightly lighter color.
        """
        _r, _g, _b = h(r), h(g), h(b)
        color = "#{}{}{}".format(_r, _g, _b)
        r = h(r + 5)
        g = h(g + 5)
        b = h(b + 5)
        focus = "#{}{}{}".format(r, g, b)
        self.set_attr_map({None: urwid.AttrSpec(color, 'default')})
        self.set_focus_map({None: urwid.AttrSpec(focus, 'default')})

    # some color helpers
    def set_white(self):
        self.set_color(9, 9, 9)

    def set_green(self):
        self.set_color(5, 9, 5)

    def set_red(self):
        self.set_color(9, 5, 5)

    def set_cyan(self):
        self.set_color(0, 9, 9)

    def set_orange(self):
        self.set_color(8, 8, 0)


class VerticalTabs(urwid.Columns):
    """
    Widget that features a vertical split with a list of tabs on one side and a
    larger area for displaying the content of the currently selected tab.
    """
    def __init__(self):
        self.tabs = {}
        self.tab_list = VerticalTabList()
        self.tab_display = TabDisplay()
        super(VerticalTabs, self).__init__([], dividechars=1)
        self.updateContent()
        self.connectSignals()

    def connectSignals(self):
        """Show content of a clicked tab"""
        signal('tab_click').connect(self.showTab)

    def updateContent(self):
        """
        Generate the data structure that represents the column contents.
        """

        # calculate tab list width
        if self.tabs:
            width_amount=max(map(len, self.tabs.keys())) + 4
        else:
            width_amount=0

        self.contents = [
            (self.tab_list, self.options(width_type='given',
                                         width_amount=width_amount)),
            # vertical divider
            (urwid.SolidFill(VERT), self.options(width_type='given',
                                                 width_amount=1)),
            (self.tab_display, self.options(width_type='weight')),
        ]

        self.focus_position = 0

    def keypress(self, size, key):
        """
        When keys are pressed make sure the current tab is being shown.
        """
        retval = super(VerticalTabs, self).keypress(size, key)
        focus = self.tab_list.focus
        self.showTab(focus)
        return retval

    def addTab(self, label, content):
        """
        Add a new tab with the given label and content widget.
        """
        new_tab = Tab(label, content)
        self.tabs[label] = new_tab
        self.tab_list.append(new_tab)
        self.updateContent()
        return new_tab

    def showTab(self, tab):
        """
        Show the given Tab instance.
        """
        self.tab_display.show(tab)
        self.updateContent()

