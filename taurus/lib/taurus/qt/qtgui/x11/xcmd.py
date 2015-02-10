# -*- coding: utf-8 -*-

#############################################################################
##
## This file is part of Taurus, a Tango User Interface Library
##
## http://www.tango-controls.org/static/taurus/latest/doc/html/index.html
##
## Copyright 2011 CELLS / ALBA Synchrotron, Bellaterra, Spain
##
## Taurus is free software: you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## Taurus is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with Taurus.  If not, see <http://www.gnu.org/licenses/>.
##
#############################################################################

"""
A XCommandWidget that may run any command

.. note:: this widget only works on X11 systems.

Example::

    from taurus.external.qt import Qt
    from taurus.qt.qtgui.application import TaurusApplication
    from taurus.qt.qtgui.x11.xcmd import XCommandWidget

    app = TaurusApplication()
    cmdWidget = XCommandWidget()
    cmdWidget.command = 'xterm'
    cmdWidget.winIdParam = '-into'
    cmdWidget.start()
    cmdWidget.show()

    app.exec_()
"""

__all__ = ["XCommandWidget", "XCommandWindow"]

import os
import signal
import weakref

from taurus.core.util import log
from taurus.external.qt import Qt
from taurus.qt.qtgui.resource import getThemeIcon
from taurus.qt.qtgui.util.taurusactionfactory import ActionFactory


class _FakeX11EmbedContainter(Qt.QLabel):
    clientClosed = Qt.Signal()
    error = Qt.Signal()

    def __init__(self, *args, **kwargs):
        Qt.QLabel.__init__(self, *args, **kwargs)
        self.setAlignment(Qt.Qt.AlignLeft | Qt.Qt.AlignTop)
        self.setStyleSheet("QLabel { background-color:black; color:white; }");
        self.setFont(Qt.QFont("Monospace"))
        if not self.text():
            self.setText("fake:~ % ")


class XCommandWidget(Qt.QWidget):
    """
    A widget displaying an X11 window inside from a command. Example::

        from taurus.external.qt import Qt
        from taurus.qt.qtgui.application import TaurusApplication
        from taurus.qt.qtgui.x11.xcmd import XCommandWidget

        app = TaurusApplication()
        cmdWidget = XCommandWidget()
        cmdWidget.command = 'xterm'
        cmdWidget.winIdParam = '-into'
        cmdWidget.show()
        cmdWidget.start()

        app.exec_()

    By default, the widget is set to auto restart if it detects that the
    underlying process the widget embeds finishes.

    By default, the widget is set to *not* auto update. This means you have
    to explicitly call `start()`.
    """

    DefaultAutoRestart = True
    DefaultAutoUpdate = False
    DefaultWinIdParam = ''
    DefaultExtraParams = ''

    commandChanged = Qt.Signal()

    def __init__(self, parent=None, designMode=False):
        Qt.QWidget.__init__(self, parent)
        self.__command = None
        self.__winIdParam = None
        self.__extraParams = []
        self.__autoRestart = False # Must be False!
        self.__autoUpdate = False
        self.__pid = None
        self.__idle = Qt.QTimer(self)
        self.__idle.timeout.connect(self.__start)
        self.__designMode = designMode
        if designMode:
            self.__x11Widget = self._getDesignModeWidget()
        else:
            self.__x11Widget = Qt.QX11EmbedContainer(self)
            self.__x11Widget.error.connect(self.__onError)
        Qt.qApp.aboutToQuit.connect(self.__onQuit)

        layout = Qt.QVBoxLayout(self)
        layout.setMargin(0)
        layout.setSpacing(0)
        layout.addWidget(self.__x11Widget)

        self.resetAutoUpdate()
        self.resetCommand()
        self.resetWinIdParam()
        self.resetExtraParams()
        self.resetAutoRestart()

    def __del__(self):
        self.terminate()

    def __onError(self, error):
        log.error("XEmbedContainer: Error")
        log.debug("XEmbedContainer: Error details: %s", error)

    def __isRunning(self):
        return self.__pid is not None and self.__pid > 0

    def __onQuit(self):
        self.autoRestart = False
        self.terminate()

    def __start(self):
        if self.__designMode:
            return
        self.__idle.stop()
        cmd = [self.command, self.winIdParam, str(self.getX11WinId())] + \
               self._getExtraParams()
        self.__pid = os.fork()
        if not self.__pid:
            # child exec the command
            cmd = ['/usr/bin/env', 'env'] + cmd
            os.execl(*cmd)
            os.exit()
        else:
            log.debug("Running: %s", " ".join(cmd))

    def _getDesignModeWidget(self):
        return _FakeX11EmbedContainter()

    def _getExtraParams(self):
        return self.extraParams.split()

    def getX11Widget(self):
        """
        Returns the X11 embed container widget.

        :return: the X11 embed container widget
        :rtype: Qt.QX11EmbedContainer
        """
        return self.__x11Widget

    def getX11WinId(self):
        """
        Returns the X11 window ID of the embeded window.

        :return: the X11 window ID of the embeded window
        :rtype: int
        """
        return self.getX11Widget().winId()

    @Qt.Slot()
    def start(self):
        """
        Starts the underlying command embedding its window in this widget.
        """
        if self.__isRunning():
            os.waitpid(self.__pid, os.WNOHANG)
            self.__pid = None
        self.__idle.start(0)

    @Qt.Slot()
    def restart(self):
        """
        Restarts the underlying command embedding its window in this widget.
        """
        if self.autoRestart:
            if self.__isRunning():
                self.terminate()
            else:
                self.start()
        else:
            self.terminate()
            self.start()

    @Qt.Slot()
    def kill(self):
        """
        Kills the underlying command. If no command is being run nothing
        happens.
        """
        if self.__isRunning():
            os.kill(self.__pid, signal.SIGKILL)
            self.__pid = None

    @Qt.Slot()
    def terminate(self):
        """
        Terminates the underlying command. If no command is being run nothing
        happens.
        """
        if self.__isRunning():
            os.kill(self.__pid, signal.SIGTERM)
            self.__pid = None

    def sizeHint(self):
        return Qt.QSize(320, 240)

    @classmethod
    def getQtDesignerPluginInfo(cls):
        return dict(label="X11 Command Widget",
                    icon=":/designer/xorg.png",
                    module="taurus.qt.qtgui.x11.xcmd",
                    group="Taurus X11 Widgets",
                    tooltip="XCommand widget")

    # Qt Properties

    def getCommand(self):
        """
        Returns the current command name

        :return: the current command name
        :rtype: str
        """
        return str(self.__command)

    @Qt.Slot(str)
    def setCommand(self, command):
        """
        Sets the current command name. Emits *commandChanged* signal.

        :param command: command name
        :type command: str
        """
        self.__command = command
        if command is None:
            self.setWindowTitle("<None>")
        else:
            self.setWindowTitle(command)
        self.commandChanged.emit()

    def resetCommand(self):
        """
        Resets the command name to None. Emits *commandChanged* signal.
        """
        self.setCommand(None)

    def getWinIdParam(self):
        """
        Returns the current window id parameter name.

        :return: the current window id parameter name
        :rtype: str
        """
        return str(self.__winIdParam)

    @Qt.Slot(str)
    def setWinIdParam(self, winIdParam):
        """
        Sets the current window id parameter name.
        Emits *commandChanged* signal.

        :param winIdParam: window id parameter name.
        :type winIdParam: str
        """
        self.__winIdParam = winIdParam
        self.commandChanged.emit()

    def resetWinIdParam(self):
        """
        Resets the command name to default. Emits *commandChanged* signal.
        """
        self.setWinIdParam(self.DefaultWinIdParam)

    @Qt.Slot(str)
    def setExtraParams(self, params):
        """
        Sets extra parameters to the command line (they should be space
        sepated). Emits *commandChanged* signal.

        :param params: extra parameters string
        :type params: str
        """
        self.__extraParams = params
        self.commandChanged.emit()

    def getExtraParams(self):
        """
        Returns the current extra parameters string.

        :return: the current extra parameters string
        :rtype: str
        """
        return self.__extraParams

    def resetExtraParams(self):
        """
        Resets the extra paramters to default. Emits *commandChanged* signal.
        """
        self.setExtraParams(self.DefaultExtraParams)

    @Qt.Slot(bool)
    def setAutoRestart(self, yesno):
        """
        (De)activates the widget auto restart. If auto restart is enabled,
        when the underlying process dies it is imediately restarted.

        :param yesno: if True enables auto restart
        :type yesno: bool
        """
        if yesno == self.__autoRestart:
            return
        self.__autoRestart = yesno
        x11Widget = self.getX11Widget()
        if yesno:
            f = x11Widget.clientClosed.connect
        else:
            f = x11Widget.clientClosed.disconnect
        f(self.start)

    def getAutoRestart(self):
        """
        Returns the current auto restart status.

        :return: True if auto restart is set or False otherwise
        :rtype: str
        """
        return self.__autoRestart

    def resetAutoRestart(self):
        """
        Resets the auto restart back to default (True).
        """
        return self.setAutoRestart(self.DefaultAutoRestart)

    @Qt.Slot(bool)
    def setAutoUpdate(self, yesno):
        """
        (De)activates the widget auto update. If auto update is enabled,
        when the underlying command changes (either due to command, winIdParam
        or extraParams changed), the process is imediately restarted.

        :param params: extra parameters string
        :type command: str
        """
        if yesno == self.__autoUpdate:
            return
        self.__autoUpdate = yesno
        x11Widget = self.getX11Widget()
        if yesno:
            f = self.commandChanged.connect
        else:
            f = self.commandChanged.disconnect
        f(self.restart)

    def getAutoUpdate(self):
        """
        Returns the current auto update status.

        :return: True if auto update is set or False otherwise
        :rtype: str
        """
        return self.__autoUpdate

    def resetAutoUpdate(self):
        """
        Resets the auto update back to default (True).
        """
        return self.setAutoUpdate(self.DefaultAutoUpdate)

    #:
    #: This property holds the widget command name (ex: xterm)
    #:
    command = Qt.Property(str, getCommand, setCommand, resetCommand)

    #:
    #: This property holds the command parameter name which specifies the
    #: window ID (ex: for xterm is *-into*)
    #:
    winIdParam = Qt.Property(str, getWinIdParam, setWinIdParam,
                                 resetWinIdParam)

    #:
    #: A space separated list of extra parameters
    #:
    extraParams = Qt.Property(str, getExtraParams, setExtraParams,
                              resetExtraParams)

    #:
    #: Specifies if widget is has auto restart mode enabled or not
    #:
    autoRestart = Qt.Property(bool, getAutoRestart, setAutoRestart,
                              resetAutoRestart)

    #:
    #: Specifies if widget is has auto update mode enabled or not
    #:
    autoUpdate = Qt.Property(bool, getAutoUpdate, setAutoUpdate,
                             resetAutoUpdate)


class XCommandWindow(Qt.QMainWindow):
    """
    The QMainWindow version of :class:`XCommandWidget`. Example::

        from taurus.external.qt import Qt
        from taurus.qt.qtgui.application import TaurusApplication
        from taurus.qt.qtgui.x11 import XCommandWindow

        app = TaurusApplication()
        cmdWindow = XCommandWindow()
        cmdWindow.command = 'xterm'
        cmdWindow.winIdParam = '-into'
        cmdWindow.show()
        cmdWindow.start()

        app.exec_()

    By default, the widget is set to auto restart if it detects that the
    underlying process the widget embeds finishes.

    By default, the widget is set to *not* auto update. This means you have
    to explicitly call `start()`.

    """

    Widget = XCommandWidget

    def __init__(self, parent=None, designMode=False, **kwargs):
        flags = kwargs.pop('flags', Qt.Qt.WindowFlags())
        super(XCommandWindow, self).__init__(parent=parent, flags=flags)
        x11 = self.Widget(parent=self, designMode=designMode, **kwargs)
        self.setCentralWidget(x11)
        toolBar = self.addToolBar("Actions")
        self.__actionsToolBar = weakref.ref(toolBar)
        action_factory = ActionFactory()
        self.__restartAction = action_factory.createAction(self,
                                      text="Restart",
                                      icon=getThemeIcon("view-refresh"),
                                      tip="restart the current command",
                                      triggered=self.restart)
        toolBar.addAction(self.__restartAction)

    def XWidget(self):
        """
        Returns the X11 widget

        :return: the X11 widget
        :rtype: Qt.QWidget
        """
        return self.centralWidget()

    @Qt.Slot()
    def start(self):
        self.XWidget().start()

    @Qt.Slot()
    def restart(self):
        self.XWidget().restart()

    @Qt.Slot()
    def terminate(self):
        self.XWidget().terminate()

    @Qt.Slot()
    def kill(self):
        self.XWidget().kill()

    def getCommand(self):
        return self.XWidget().command

    @Qt.Slot(str)
    def setCommand(self, command):
        self.XWidget().command = command

    def resetCommand(self):
        self.XWidget().resetCommand()

    def getWinIdParam(self):
        return self.XWidget().winIdParam

    @Qt.Slot(str)
    def setWinIdParam(self, winIdParam):
        self.XWidget().winIdParam = winIdParam

    def resetWinIdParam(self):
        self.XWidget().resetWinIdParam()

    @Qt.Slot(str)
    def setExtraParams(self, params):
        self.XWidget().extraParams = params

    def getExtraParams(self):
        return self.XWidget().extraParams

    def resetExtraParams(self):
        self.XWidget().resetExtraParams()

    @Qt.Slot(bool)
    def setAutoRestart(self, yesno):
        self.XWidget().autoRestart = yesno

    def getAutoRestart(self):
        return self.XWidget().autoRestart

    def resetAutoRestart(self):
        self.XWidget().resetAutoRestart()

    @Qt.Slot(bool)
    def setAutoUpdate(self, yesno):
        self.XWidget().autoUpdate = yesno

    def getAutoUpdate(self):
        return self.XWidget().autoUpdate

    def resetAutoUpdate(self):
        self.XWidget().resetAutoUpdate()

    @classmethod
    def getQtDesignerPluginInfo(cls):
        return dict(label="X11 Command Window",
                    icon=":/designer/xorg.png",
                    module="taurus.qt.qtgui.x11.xcmd",
                    group="Taurus X11 Widgets",
                    tooltip="XCommand window")

    start.__doc__ = Widget.start.__doc__
    restart.__doc__ = Widget.restart.__doc__
    terminate.__doc__ = Widget.terminate.__doc__
    kill.__doc__ = Widget.kill.__doc__
    getCommand.__doc__ = Widget.getCommand.__doc__
    setCommand.__doc__ = Widget.setCommand.__doc__
    resetCommand.__doc__ = Widget.resetCommand.__doc__
    getWinIdParam.__doc__ = Widget.getWinIdParam.__doc__
    setWinIdParam.__doc__ = Widget.setWinIdParam.__doc__
    resetWinIdParam.__doc__ = Widget.resetWinIdParam.__doc__
    setExtraParams.__doc__ = Widget.setExtraParams.__doc__
    getExtraParams.__doc__ = Widget.getExtraParams.__doc__
    resetExtraParams.__doc__ = Widget.resetExtraParams.__doc__
    setAutoRestart.__doc__ = Widget.setAutoRestart.__doc__
    getAutoRestart.__doc__ = Widget.getAutoRestart.__doc__
    resetAutoRestart.__doc__ = Widget.resetAutoRestart.__doc__
    setAutoUpdate.__doc__ = Widget.setAutoUpdate.__doc__
    getAutoUpdate.__doc__ = Widget.getAutoUpdate.__doc__
    resetAutoUpdate.__doc__ = Widget.resetAutoUpdate.__doc__

    #:
    #: This property holds the widget command name (ex: xterm)
    #:
    command = Qt.Property(str, getCommand, setCommand, resetCommand)

    #:
    #: This property holds the command parameter name which specifies the
    #: window ID (ex: for xterm is *-into*)
    #:
    winIdParam = Qt.Property(str, getWinIdParam, setWinIdParam,
                                 resetWinIdParam)

    #:
    #: A space separated list of extra parameters
    #:
    extraParams = Qt.Property(str, getExtraParams, setExtraParams,
                              resetExtraParams)
    #:
    #: Specifies if widget is has auto restart mode enabled or not
    #:
    autoRestart = Qt.Property(bool, getAutoRestart, setAutoRestart,
                              resetAutoRestart)
    #:
    #: Specifies if widget is has auto update mode enabled or not
    #:
    autoUpdate = Qt.Property(bool, getAutoUpdate, setAutoUpdate,
                             resetAutoUpdate)

def main():
    from taurus.qt.qtgui.application import TaurusApplication

    app = TaurusApplication([])
    w = XCommandWindow()
    w.setFixedSize(800, 600)
    w.command = 'xterm'
    w.winIdParam = '-into'
    w.show()
    w.start()
    app.exec_()

if __name__ == "__main__":
    main()