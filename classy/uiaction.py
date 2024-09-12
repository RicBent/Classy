import ida_kernwin


class UiAction(ida_kernwin.action_handler_t):

    def __init__(self, id, name, tooltip, menu_path, callback, shortcut):
        ida_kernwin.action_handler_t.__init__(self)
        self.id = id
        self.name = name
        self.tooltip = tooltip
        self.menu_path = menu_path
        self.callback = callback
        self.shortcut = shortcut


    def register(self):
        action_desc = ida_kernwin.action_desc_t(self.id, self.name, self, self.shortcut, self.tooltip)
        if not ida_kernwin.register_action(action_desc):
            return False
        if not ida_kernwin.attach_action_to_menu(self.menu_path, self.id, 0):
            return False
        return True


    def unregister(self):
        self.detach()
        ida_kernwin.unregister_action(self.id)


    def attach(self):
        return ida_kernwin.attach_action_to_menu(self.menu_path, self.id, 0)


    def detach(self):
        ida_kernwin.detach_action_from_menu(self.menu_path, self.id)


    def activate(self, ctx):
        self.callback()
        return 1


    def update(self, ctx):
        return ida_kernwin.AST_ENABLE_FOR_IDB
