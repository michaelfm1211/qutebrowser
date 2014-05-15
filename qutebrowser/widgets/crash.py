# Copyright 2014 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""The dialog which gets shown when qutebrowser crashes."""

import sys
import traceback
from urllib.error import URLError

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QClipboard
from PyQt5.QtWidgets import (QDialog, QLabel, QTextEdit, QPushButton,
                             QVBoxLayout, QHBoxLayout, QApplication)

import qutebrowser.config.config as config
import qutebrowser.utils.misc as utils
from qutebrowser.utils.version import version


class _CrashDialog(QDialog):

    """Dialog which gets shown after there was a crash.

    Attributes:
        These are just here to have a static reference to avoid GCing.
        _vbox: The main QVBoxLayout
        _lbl: The QLabel with the static text
        _txt: The QTextEdit with the crash information
        _hbox: The QHboxLayout containing the buttons
        _url: Pastebin URL QLabel.
        _crash_info: A list of tuples with title and crash information.
    """

    def __init__(self):
        """Constructor for CrashDialog."""
        super().__init__()
        self._crash_info = None
        self._hbox = None
        self._lbl = None
        self._gather_crash_info()
        self.setFixedSize(500, 350)
        self.setWindowTitle("Whoops!")
        self._vbox = QVBoxLayout(self)
        self._init_text()
        self._txt = QTextEdit()
        self._txt.setText(self._format_crash_info())
        self._vbox.addWidget(self._txt)
        self._url = QLabel()
        self._set_text_flags(self._url)
        self._vbox.addWidget(self._url)
        self._init_buttons()

    def _init_text(self):
        """Initialize the main text to be displayed on an exception.

        Should be extended by superclass to set the actual text."""
        self._lbl = QLabel()
        self._lbl.setWordWrap(True)
        self._set_text_flags(self._lbl)
        self._vbox.addWidget(self._lbl)

    def _init_buttons(self):
        """Initialize the buttons.

        Should be extended by superclass to provide the actual buttons.
        """
        self._hbox = QHBoxLayout()
        self._hbox.addStretch()
        self._vbox.addLayout(self._hbox)

    def _set_text_flags(self, obj):
        """Set text interaction flags of a widget to allow link clicking.

        Args:
            obj: A QLabel.
        """
        obj.setTextInteractionFlags(Qt.TextSelectableByMouse |
                                    Qt.TextSelectableByKeyboard |
                                    Qt.LinksAccessibleByMouse |
                                    Qt.LinksAccessibleByKeyboard)

    def _gather_crash_info(self):
        """Gather crash information to display.

        Args:
            pages: A list of the open pages (URLs as strings)
            cmdhist: A list with the command history (as strings)
            exc: An exception tuple (type, value, traceback)
        """
        self._crash_info = [
            ("Version info", version()),
            ("Commandline args", ' '.join(sys.argv[1:])),
        ]
        try:
            self._crash_info.append(("Config",
                                     config.instance().dump_userconfig()))
        except AttributeError:
            pass

    def _format_crash_info(self):
        """Format the gathered crash info to be displayed.

        Return:
            The string to display.
        """
        chunks = []
        for (header, body) in self._crash_info:
            if body is not None:
                h = '==== {} ===='.format(header)
                chunks.append('\n'.join([h, body]))
        return '\n\n'.join(chunks)

    def pastebin(self):
        """Paste the crash info into the pastebin."""
        try:
            url = utils.pastebin(self._txt.toPlainText())
        except (URLError, ValueError) as e:
            self._url.setText('Error while pasting: {}'.format(e))
            return
        self._btn_pastebin.setEnabled(False)
        self._url.setText("URL copied to clipboard: "
                          "<a href='{}'>{}</a>".format(url, url))
        QApplication.clipboard().setText(url, QClipboard.Clipboard)


class ExceptionCrashDialog(_CrashDialog):

    """Dialog which gets shown on an exception.

    Attributes:
        _btn_quit: The quit button
        _btn_restore: the restore button
        _btn_pastebin: the pastebin button
        _pages: A list of the open pages (URLs as strings)
        _cmdhist: A list with the command history (as strings)
        _exc: An exception tuple (type, value, traceback)
    """

    def __init__(self, pages, cmdhist, exc):
        self._pages = pages
        self._cmdhist = cmdhist
        self._exc = exc
        self._btn_quit = None
        self._btn_restore = None
        self._btn_pastebin = None
        super().__init__()
        self.setModal(True)

    def _init_text(self):
        super()._init_text()
        text = ("Argh! qutebrowser crashed unexpectedly.<br/>"
                "Please review the info below to remove sensitive data and "
                "then submit it to <a href='mailto:crash@qutebrowser.org'>"
                "crash@qutebrowser.org</a> or click 'pastebin'.<br/><br/>")
        if self._pages:
            text += ("You can click 'Restore tabs' to attempt to reopen your "
                     "open tabs.")
        self._lbl.setText(text)

    def _init_buttons(self):
        super()._init_buttons()
        self._btn_quit = QPushButton()
        self._btn_quit.setText("Quit")
        self._btn_quit.clicked.connect(self.reject)
        self._hbox.addWidget(self._btn_quit)
        self._btn_pastebin = QPushButton()
        self._btn_pastebin.setText("Pastebin")
        self._btn_pastebin.clicked.connect(self.pastebin)
        self._hbox.addWidget(self._btn_pastebin)
        if self._pages:
            self._btn_restore = QPushButton()
            self._btn_restore.setText("Restore tabs")
            self._btn_restore.clicked.connect(self.accept)
            self._btn_restore.setDefault(True)
            self._hbox.addWidget(self._btn_restore)

    def _gather_crash_info(self):
        super()._gather_crash_info()
        self._crash_info += [
            ("Exception", ''.join(traceback.format_exception(*self._exc))),
            ("Open Pages", '\n'.join(self._pages)),
            ("Command history", '\n'.join(self._cmdhist)),
        ]


class FatalCrashDialog(_CrashDialog):

    """Dialog which gets shown when a fatal error occured.

    Attributes:
        _log: The log text to display.
        _btn_ok: The OK button.
        _btn_pastebin: The pastebin button.
    """

    def __init__(self, log):
        self._log = log
        self._btn_ok = None
        self._btn_pastebin = None
        super().__init__()

    def _init_text(self):
        super()._init_text()
        text = ("qutebrowser was restarted after a fatal crash.<br/>"
                "Please click on 'pastebin' or send the data below to "
                "<a href='mailto:crash@qutebrowser.org'>"
                "crash@qutebrowser.org</a>.<br/><br/>")
        self._lbl.setText(text)

    def _init_buttons(self):
        super()._init_buttons()
        self._btn_ok = QPushButton()
        self._btn_ok.setText("OK")
        self._btn_ok.clicked.connect(self.accept)
        self._hbox.addWidget(self._btn_ok)
        self._btn_pastebin = QPushButton()
        self._btn_pastebin.setText("Pastebin")
        self._btn_pastebin.clicked.connect(self.pastebin)
        self._hbox.addWidget(self._btn_pastebin)

    def _gather_crash_info(self):
        super()._gather_crash_info()
        self._crash_info += [
            ("Fault log", self._log),
        ]
