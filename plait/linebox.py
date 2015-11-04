# -*- coding: utf-8 -*-

import urwid

NONE = ' '
VERT = u'│'
HORI = u'─'

class BorderBox(urwid.LineBox):
    @property
    def original_widget(self):
        return self._w

    @original_widget.setter
    def original_widget(self, w):
        self._w = w


def noBorder():
    return dict(
        tline=NONE, bline=NONE,
        lline=NONE, rline=NONE,
        tlcorner=NONE, blcorner=NONE,
        trcorner=NONE, brcorner=NONE)

def leftBorder():
    return dict(
        tline=NONE, bline=NONE,
        lline=VERT, rline=NONE,
        tlcorner=NONE, blcorner=NONE,
        trcorner=NONE, brcorner=NONE)

def rightBorder():
    return dict(
        tline=NONE, bline=NONE,
        lline=NONE, rline=VERT,
        tlcorner=NONE, blcorner=NONE,
        trcorner=NONE, brcorner=NONE)

def topBorder():
    return dict(
        tline=HORI, bline=NONE,
        lline=NONE, rline=NONE,
        tlcorner=NONE, blcorner=NONE,
        trcorner=NONE, brcorner=NONE)

def bottomBorder():
    return dict(
        tline=NONE, bline=HORI,
        lline=NONE, rline=NONE,
        tlcorner=NONE, blcorner=NONE,
        trcorner=NONE, brcorner=NONE)

def horizontalBorder():
    return dict(
        tline=HORI, bline=HORI,
        lline=NONE, rline=NONE,
        tlcorner=NONE, blcorner=NONE,
        trcorner=NONE, brcorner=NONE)

def verticalBorder():
    return dict(
        tline=NONE, bline=NONE,
        lline=VERT, rline=VERT,
        tlcorner=NONE, blcorner=NONE,
        trcorner=NONE, brcorner=NONE)

def cornersBorder():
    return dict(
        tline=NONE, bline=NONE,
        lline=NONE, rline=NONE)
