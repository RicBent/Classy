import idaapi
import idc
import ida_bytes

import classy.database as database
import classy.itanium_mangler as itanium_mangler


class Class(object):
    def __init__(self, name, base):

        self.name = name

        self.base = base
        self.derived = []

        self.struct_id = idc.BADADDR

        if self.base is not None:
            self.base.derived.append(self)

        self.methods = []

        self.vtable_start = None
        self.vtable_end = None
        self.vmethods = []
        self.reset_vtable()

        db = database.get()
        db.classes_by_name[name] = self
        if self.base is None:
            db.root_classes.append(self)


    def unlink(self, delete_orphaned_struct=False):
        if len(self.derived) > 0:
            raise ValueError('Cannot unlink classes with derived classes')

        for m in self.methods:
            m.unlink()

        for vm in self.vmethods:
            if vm.owner == self:
                vm.unlink()

        self.unlink_struct(delete_orphaned_struct)

        if self.base is not None:
            self.base.derived.remove(self)

        db = database.get()
        del db.classes_by_name[self.name]
        if self.base is None:
            db.root_classes.remove(self)


    def safe_name(self):
        return Class.s_safe_name(self.name)


    @staticmethod
    def s_safe_name(name):
        return name.replace('::', '_')


    def rename(self, new_name):
        old_name = self.name

        db = database.get()
        del db.classes_by_name[old_name]
        db.classes_by_name[new_name] = self

        self.name = new_name

        # Try to rename the struct
        if self.struct_id != idc.BADADDR:
            struct_name = idc.get_struc_name(self.struct_id)
            if struct_name == Class.s_safe_name(old_name):
                idc.set_struc_name(self.struct_id, self.safe_name())

        # Rename ctors and dtors
        for vm in self.vmethods:
            if vm.name == old_name:
                vm.name = new_name
            if vm.name == f'~{old_name}':
                vm.name = f'~{new_name}'
        for m in self.methods:
            if m.name == old_name:
                m.name = new_name
            if m.name == f'~{old_name}':
                m.name = f'~{new_name}'

        self.refresh()


    def refresh(self):
        for m in self.methods:
            m.refresh()
        for m in self.vmethods:
            m.refresh()
        self.refresh_struct_comment()


    def set_vtable_range(self, start, end):
        if self.is_vtable_locked():
            raise ValueError('VTable cannot be modified because the class has derived classes')
        if start % 4 or end % 4:
            raise ValueError('VTable start and end must be 4 byte aligned')
        if start >= end:
            raise ValueError('Vtable end must be after the start')
        if self.base:
            new_len = (end - start) // 4
            if new_len < len(self.base.vmethods):
                raise ValueError('VTable is smaller than base VTable')
        # Todo: More sanity checks: Don't overwrite any other vtable

        self.reset_vtable()
        self.vtable_start = start
        self.vtable_end = end
        self.init_vtable()


    def is_vtable_locked(self):
        return len(self.derived) > 0


    def can_be_derived(self):
        if self.base is None:
            return True
        return len(self.vmethods) >= len(self.base.vmethods)    # vtable inited?


    def vtable_start_idx(self):
        return 0 if self.base is None else len(self.base.vmethods)


    def reset_vtable(self):
        if self.is_vtable_locked():
            return
        self.vtable_start = None
        self.vtable_end = None
        idx = self.vtable_start_idx()
        for vm in self.vmethods[idx:]:
            vm.unlink()
        self.vmethods = []


    def init_vtable(self):
        my_start_idx = self.vtable_start_idx()

        pointer_size = idaapi.DEF_ADDRSIZE
        # Fix: support 64bit work
        if idc.__EA64__:
            pfn_make_ptr = lambda x: ida_bytes.create_data(x, idc.FF_QWORD, 8, idaapi.BADADDR) #MakeQword
            pfn_get_ptr_value = ida_bytes.get_qword
        else:
            pfn_make_ptr =  lambda x: ida_bytes.create_data(x, idc.FF_DWORD, 4, idaapi.BADADDR) #ida_bytes.MakeDword
            pfn_get_ptr_value = ida_bytes.get_dword

        for idx, ea in enumerate(range(self.vtable_start, self.vtable_end, pointer_size)):
            pfn_make_ptr(ea)
            idc.op_plain_offset(ea, 0, 0)
            dst = pfn_get_ptr_value(ea)

            if idx < my_start_idx:
                base_method = self.base.vmethods[idx]
                if base_method.is_dst_equal(dst):                   # Method from base class
                    self.vmethods.append(self.base.vmethods[idx])
                elif Method.s_is_pure_virtual_dst(dst):             # New pure virtual override
                    opvm = PureVirtualOverrideMethod(self, base_method, idx)
                    opvm.refresh()
                    self.vmethods.append(opvm)
                elif Method.s_is_deleted_virtual_dst(dst):          # New deleted override
                    dom = DeletedOverrideMethod(self, base_method, idx)
                    dom.refresh()
                    self.vmethods.append(dom)
                else:                                               # New override
                    om = OverrideMethod(dst, self, base_method, idx)
                    om.refresh()
                    self.vmethods.append(om)
            elif Method.s_is_pure_virtual_dst(dst):                 # New pure virtual
                pvm = PureVirtualMethod(self, 'vf%X' % (idx*4), idx)
                pvm.refresh()
                self.vmethods.append(pvm)
            elif Method.s_is_deleted_virtual_dst(dst):              # New deleted virtual
                pvm = DeletedVirtualMethod(self, 'vf%X' % (idx*4), idx)
                pvm.refresh()
                self.vmethods.append(pvm)
            else:                                                   # New virtual
                vm = VirtualMethod(dst, self, 'vf%X' % (idx*4), idx)
                vm.refresh()
                self.vmethods.append(vm)


    def get_vtable_index_ea(self, idx):
        if idx > len(self.vmethods):
            raise ValueError('get_vtable_index_ea for out of range index')
        return self.vtable_start + (idx*4)


    def iter_vtable(self):
        ea = self.vtable_start
        end = self.vtable_end

        while ea <= end:
            yield (ea, idc.get_wide_dword(ea))
            ea += 4


    def set_struct_id(self, new_struct_id, delete_orphaned=False):
        db = database.get()

        if self.struct_id == new_struct_id:
            return

        if new_struct_id in db.classes_by_struct_id:
            raise ValueError(
                f'The struct is already assigned to the class {db.classes_by_struct_id[new_struct_id]}'
            ).name


        self.unlink_struct(delete_orphaned)

        self.struct_id = new_struct_id
        if self.struct_id != idc.BADADDR:
            db.classes_by_struct_id[self.struct_id] = self

        self.refresh()


    def unlink_struct(self, delete_orphaned=False):
        if self.struct_id == idc.BADADDR:
            return

        del database.get().classes_by_struct_id[self.struct_id]

        if delete_orphaned:
            idc.del_struc(self.struct_id)
        else:
            struct_name = idc.get_struc_name(self.struct_id)
            idc.set_struc_cmt(self.struct_id, f'Orphaned from {self.name}', False)
            idc.set_struc_name(self.struct_id, f'{struct_name}_orphaned')

        self.struct_id = idc.BADADDR


    def refresh_struct_comment(self):
        if self.struct_id == idc.BADADDR:
            return

        idc.set_struc_cmt(self.struct_id, f'Linked to {self.name}', False)


    def generate_cpp_definition(self):
        contents = [
            'class %s%s\n{\npublic:'
            % (
                self.name,
                '' if self.base is None else f' : public {self.base.name}',
            )
        ]

        seen_dtor = False

        # Overrides
        for idx in range(self.vtable_start_idx()):
            vm = self.vmethods[idx]
            if vm.owner == self and type(vm) == OverrideMethod:
                if vm.name == f'~{self.name}':
                    if seen_dtor:
                        continue
                    seen_dtor = True
                    contents.append(f'    virtual {vm.get_signature(include_owner=False)};')
                else:
                    contents.append(f'    {vm.get_signature(include_owner=False)} override;')

        if self.vtable_start_idx() > 0:
            contents.append('')

        # New virtuals
        for idx in range(self.vtable_start_idx(), len(self.vmethods)):
            vm = self.vmethods[idx]
            if type(vm) == VirtualMethod:   # If this isn't the case something is very wrong
                if vm.name == f'~{self.name}':
                    if seen_dtor:
                        continue
                    else:
                        seen_dtor = True
                contents.append(f'    virtual {vm.get_signature(include_owner=False)};')

        if (len(self.vmethods) - self.vtable_start_idx()) > 0:
            contents.append('')

        # Methods
        for m in self.methods:
            if m.name == f'~{self.name}':
                if seen_dtor:
                    continue
                else:
                    seen_dtor = True
            contents.append(f'    {m.get_signature(include_owner=False)};')

        # Todo: Replace this ugly temp code
        if self.struct_id != idc.BADADDR:
            struct = idaapi.get_struc(self.struct_id)
            raw_txt = idc.GetLocalType(struct.ordinal, idc.PRTYPE_1LINE)
            l_idx = raw_txt.find('{')
            r_idx = raw_txt.find('}')
            segs = raw_txt[l_idx+1:r_idx].split(';')
            if len(segs):
                contents.append('')
            contents.extend(f'    {s};' for s in segs)
        contents.append('};\n')

        return '\n'.join(contents)


    def generate_symbols(self):
        contents = ['/* %s */\n' % self.name]

        if len(self.vmethods):
            contents.append('/* virtual functions */')
            for vm in self.vmethods:
                if vm.owner == self and not vm.is_pure_virtual():
                    contents.append('%s = 0x%X;' % (vm.get_mangled(), vm.ea))
            contents.append('')

        if len(self.methods):
            contents.append('/* functions */')
            contents.extend('%s = 0x%X;' % (m.get_mangled(), m.ea) for m in self.methods)
            contents.append('')

        return '\n'.join(contents)


    @staticmethod
    def s_name_is_valid(name):

        segs = name.split('::')

        if len(segs) == 0:
            return False

        for seg in segs:
            if len(seg) < 1:
                return False

            if seg[0].isdigit():
                return False

            for c in seg:
                if not c.isalnum() and c != '_':
                    return False

        return True


    @staticmethod
    def s_create():
        db = database.get()

        name = idaapi.ask_str('', idaapi.HIST_IDENT,'Enter a class name')

        if name is None:
            return None

        if name in database.get().classes_by_name:
            idaapi.warning('That name is already used.')
            return None

        if not Class.s_name_is_valid(name):
            idaapi.warning('The class name "%s" is invalid.' % name)
            return None

        base_class = None
        base_name = idaapi.ask_str('', idaapi.HIST_IDENT,'Enter a base class name (leave empty for none)')
        if base_name is None:
            return None
        if base_name:
            if base_name not in db.classes_by_name:
                idaapi.warning('The class "%s" is not in the database.' % base_name)
                return None
            else:
                base_class = db.classes_by_name[base_name]
                if not base_class.can_be_derived():
                    idaapi.warning(
                        f'The class {base_class.name} cannot be derived because the VTable is not setup correctly'
                    )

                    return None

        return Class(name, base_class)


class Method(object):
    def __init__(self, ea, owner, name):
        self.ea = ea
        self.owner = owner
        self.name = name
        self.args = ''
        self.return_type = 'void'
        self.is_const = False
        self.ctor_type = 1
        self.dtor_type = 1

        if ea != idc.BADADDR:
            database.get().known_methods[ea] = self


    def type_name(self):
        return 'regular'


    def refresh(self):
        if self.ea != idc.BADADDR:
            mangled = self.get_mangled()
            idc.set_name(self.ea, mangled, idc.SN_CHECK)
        self.refresh_comments()


    def unlink(self):
        if self.owner and self in self.owner.methods:
            self.owner.methods.remove(self)

        self.owner = None

        if self.ea != idc.BADADDR:
            del database.get().known_methods[self.ea]
            idc.set_name(self.ea, '', idc.SN_CHECK)
            idc.set_func_cmt(self.ea, '', False)


    def is_dst_equal(self, dst):
        return dst == self.ea


    def set_signature(self, name, args, return_type='void', is_const=False, ctor_type=1, dtor_type=1):
        signature = Method.s_make_signature(self.owner, name, args, is_const, return_type)
        itanium_mangler.mangle_function(signature, database.get().typedefs, ctor_type, dtor_type)    # throws excption when invalid
        self.name = name
        self.args = args
        self.return_type = return_type
        self.is_const = is_const
        self.ctor_type = ctor_type
        self.dtor_type = dtor_type
        self.refresh()


    @staticmethod
    def s_make_signature(owner, name, args='', is_const=False, return_type=''):
        signature = f'{owner.name}::' if owner is not None else ''
        signature += name
        signature += '('
        signature += args
        signature += ')'
        if is_const:
            signature += ' const'
        if return_type:
            signature = f'{return_type} {signature}'
        return signature


    def get_signature(self, include_return_type=True, include_owner=True):
        return Method.s_make_signature(self.owner if include_owner else None, self.name, self.args, self.is_const, self.return_type if include_return_type else '')


    def get_mangled(self):
        return itanium_mangler.mangle_function(self.get_signature(), database.get().typedefs, self.ctor_type, self.dtor_type)  # throws excption when invalid


    def copy_signature(self, other):
        if other.owner is not None and other.name == f'~{other.owner.name}':
            if self.owner is None:
                raise ValueError('Cannot copy dtor to non-owned function')
            self.name = f'~{self.owner.name}'
        else:
            self.name = other.name
        self.args = other.args
        self.return_type = other.return_type
        self.is_const = other.is_const
        self.ctor_type = other.ctor_type
        self.dtor_type = other.dtor_type


    def get_mangled(self):
        demangled = self.get_signature(False)
        return itanium_mangler.mangle_function(demangled, database.get().typedefs, self.ctor_type, self.dtor_type)


    def get_comment(self):
        return ''


    def refresh_comments(self):
        if self.ea == idc.BADADDR:
            return

        if comment := self.get_comment():
            idc.set_func_cmt(self.ea, comment, False)


    @staticmethod
    def s_is_pure_virtual_dst(dst):
        return dst in database.get().pure_virtual_vals


    @staticmethod
    def s_is_deleted_virtual_dst(dst):
        return dst in database.get().deleted_virtual_vals



class VirtualMethod(Method):
    def __init__(self, ea, owner, name, vtable_idx):
        super(VirtualMethod, self).__init__(ea, owner, name)
        self.vtable_idx = vtable_idx
        self.overrides = []


    def is_override(self):
        return False


    def is_pure_virtual(self):
        return False


    def type_name(self):
        return 'virtual'


    def refresh(self):
        Method.refresh(self)


    def refresh_comments(self):
        Method.refresh_comments(self)
        idc.set_cmt(self.owner.get_vtable_index_ea(self.vtable_idx), self.get_vtable_comment(), 0) 


    def unlink(self):
        if len(self.overrides) > 0:
            raise ValueError('Cannot unlink method with overrides')
        for i, vm in enumerate(self.owner.vmethods):
            if vm == self:
                self.owner.vmethods[i] = None
        Method.unlink(self)


    def set_signature(self, name, args, return_type='void', is_const=False, ctor_type=1, dtor_type=1):
        Method.set_signature(self, name, args, return_type, is_const, ctor_type, dtor_type)
        for o in self.overrides:
            o.propagate_signature()


    def get_comment(self):
        lines = []

        if len(self.overrides) > 0:
            lines.append('Overridden by:')
            for o in self.overrides:
                if not o.is_pure_virtual():
                    lines.append('  - 0x%X : %s' % (o.ea, o.owner.name))
                else:
                    lines.append(f'  - pure virtual : {o.owner.name}')
        else:
            lines.append('Overridden by: None')

        return "\n".join(lines)


    def get_vtable_comment(self):
        return ''


    def add_override(self, override):
        if override in self.overrides:
            return
        self.overrides.append(override)
        self.refresh_comments()


    def remove_override(self, override):
        if override not in self.overrides:
            return
        self.overrides.remove(override)
        self.refresh_comments()



class PureVirtualMethod(VirtualMethod):
    def __init__(self, owner, name, vtable_idx):
        super(PureVirtualMethod, self).__init__(idc.BADADDR, owner, name, vtable_idx)


    def is_pure_virtual(self):
        return True


    def type_name(self):
        return 'pure virtual'


    def is_dst_equal(self, dst):
        return Method.s_is_pure_virtual_dst(dst)


    def get_comment(self):
        return ''


    def get_vtable_comment(self):
        return self.get_signature()



class DeletedVirtualMethod(PureVirtualMethod):
    def __init__(self, owner, name, vtable_idx):
        super(DeletedVirtualMethod, self).__init__(owner, name, vtable_idx)


    def type_name(self):
        return 'deleted virtual'


    def is_dst_equal(self, dst):
        return Method.s_is_deleted_virtual_dst(dst)



class OverrideMethod(VirtualMethod):
    def __init__(self, ea, owner, base, vtable_idx):
        if not base.owner.can_be_derived():
            raise ValueError('Overriding function of class without inited VTable')
        super(OverrideMethod, self).__init__(ea, owner, base.name, vtable_idx)
        self.base = base
        self.base.add_override(self)
        self.copy_signature(base)


    def is_override(self):
        return True


    def type_name(self):
        return 'override'


    def unlink(self):
        self.base.remove_override(self)
        VirtualMethod.unlink(self)


    def set_signature(self, name, args, return_type='void', is_const=False, ctor_type=1, dtor_type=1):
        root_method = self.get_root_method()

        if name == f'~{self.owner.name}':
            root_name = f'~{root_method.owner.name}'
        else:
            root_name = name

        root_method.set_signature(root_name, args, return_type, is_const, ctor_type, dtor_type)


    def propagate_signature(self):
        self.copy_signature(self.base)
        self.refresh()
        for o in self.overrides:
            o.propagate_signature()


    def get_root_method(self):
        method = self
        while method.is_override():
            method = method.base
        return method


    def get_comment(self):
        if self.base.is_pure_virtual():
            override_cmt = 'pure virtual'
        else:
            override_cmt = '0x%X' % self.base.ea
        return 'Overrides: %s : %s\n\n%s' % (self.base.owner.name, override_cmt, VirtualMethod.get_comment(self))



class PureVirtualOverrideMethod(OverrideMethod):
    def __init__(self, owner, base, vtable_idx):
        super(PureVirtualOverrideMethod, self).__init__(idc.BADADDR, owner, base, vtable_idx)


    def is_pure_virtual(self):
        return True


    def type_name(self):
        return 'pure virtual override'


    def is_dst_equal(self, dst):
        return Method.s_is_pure_virtual_dst(dst)


    def get_comment(self):
        return ''


    def get_vtable_comment(self):
        return self.get_signature()



class DeletedOverrideMethod(PureVirtualOverrideMethod):
    def __init__(self, owner, base, vtable_idx):
        super(DeletedOverrideMethod, self).__init__(owner, base, vtable_idx)


    def type_name(self):
        return 'deleted override'


    def is_dst_equal(self, dst):
        return Method.s_is_deleted_virtual_dst(dst)



class NullMethod(Method):
    def __init__(self, owner):
        super(NullMethod, self).__init__(idc.BADADDR, owner, 'NullMethod')


    def type_name(self):
        return 'null'


    def refresh(self):
        pass


    def unlink(self):
        pass



def refresh_all():
    db = database.get()

    for c in db.classes_by_name.values():
        c.refresh()
