import idaapi
from PyQt5 import QtWidgets, QtCore
from classy.aboutwindow import AboutWindow


def ask_yes_no(text, yes_is_default = True):
    ret = QtWidgets.QMessageBox.question(None, "Classy", text,
                                         QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                         defaultButton=(QtWidgets.QMessageBox.Yes
                                                        if yes_is_default else
                                                        QtWidgets.QMessageBox.No))

    return ret == QtWidgets.QMessageBox.Yes


def log(msg):
    idaapi.msg("[ClassyDX] %s\n" % str(msg))


def show_about():
    AboutWindow().exec_()



class ClickableQLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()
    doubleClicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtWidgets.QLabel.__init__(self, parent)

    def mousePressEvent(self, ev):
        self.clicked.emit()

    def mouseDoubleClickEvent(self, ev):
        self.doubleClicked.emit()



class EnterPressQTableWidget(QtWidgets.QTableWidget):
    cellEnterPressed = QtCore.pyqtSignal(int, int)

    def __init__(self, parent=None):
        super(EnterPressQTableWidget, self).__init__(parent)

    def keyPressEvent(self, event):
        if event.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
            row = self.currentRow()
            column = self.currentColumn()
            if row >= 0 and column >= 0:
                self.cellEnterPressed.emit(row, column)
                return
        super(EnterPressQTableWidget, self).keyPressEvent(event)


def main_window():
    tform = idaapi.get_current_widget()

    if not tform:
        tform = idaapi.find_widget('Output window')

    widget = idaapi.PluginForm.FormToPyQtWidget(tform)
    window = widget.window()
    return window
