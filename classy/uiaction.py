import idaapi


class UiAction(idaapi.action_handler_t):

    def __init__(self, id, name, tooltip, menu_path, callback, shortcut):
        idaapi.action_handler_t.__init__(self)
        self.id = id
        self.name = name
        self.tooltip = tooltip
        self.menu_path = menu_path
        self.callback = callback
        self.shortcut = shortcut


    def register(self):
        action_desc = idaapi.action_desc_t(self.id, self.name, self, self.shortcut, self.tooltip)
        if not idaapi.register_action(action_desc):
            return False
        if not idaapi.attach_action_to_menu(self.menu_path, self.id, 0):
            return False
        return True


    def unregister(self):
        self.detach()
        idaapi.unregister_action(self.id)


    def attach(self):
        return idaapi.attach_action_to_menu(self.menu_path, self.id, 0)


    def detach(self):
        idaapi.detach_action_from_menu(self.menu_path, self.id)


    def activate(self, ctx):
        self.callback()
        return 1


    def update(self, ctx):
        return idaapi.AST_ENABLE_FOR_IDB
