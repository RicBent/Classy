import idaapi
import idc
from sark.qt import QtWidgets, QtCore
from aboutwindow import AboutWindow


class UiAction(idaapi.action_handler_t):

    def __init__(self, id, name, tooltip, menu_path, callback, shortcut):
        idaapi.action_handler_t.__init__(self)
        self.id = id
        self.name = name
        self.tooltip = tooltip
        self.menu_path = menu_path
        self.callback = callback
        self.shortcut = shortcut

    def register_action(self):
        action_desc = idaapi.action_desc_t(self.id, self.name, self, self.shortcut, self.tooltip)
        if not idaapi.register_action(action_desc):
            return False
        if not idaapi.attach_action_to_menu(self.menu_path, self.id, 0):
            return False
        return True

    def unregister_action(self):
        idaapi.detach_action_from_menu(self.menu_path, self.id)
        idaapi.unregister_action(self.id)

    def activate(self, ctx):
        self.callback()
        return 1

    def update(self, ctx):
        return idaapi.AST_ENABLE_FOR_IDB


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
