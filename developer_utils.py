# -*- coding: utf-8 -*-

import os
import pkgutil
import importlib


def setup_addon_modules(path, package_name, reload):

    def get_submodule_names(path=path[0], root=''):
        module_names = []
        for importer, module_name, is_package in pkgutil.iter_modules([path]):
            if is_package:
                sub_path = os.path.join(path, module_name)
                sub_root = root + module_name + '.'
                if os.path.basename(sub_path) != 'assets':
                    module_names.extend(get_submodule_names(sub_path, sub_root))
            else:
                module_names.append(root + module_name)
        return module_names

    def import_submodules(names):
        modules = []
        for name in names:
            modules.append(importlib.import_module('.' + name, package_name))
        return modules
        
    def reload_modules(modules):
        for module in modules:
            importlib.reload(module)
    
    names = get_submodule_names()
    modules = import_submodules(names)        
    if reload: 
        reload_modules(modules) 
    return modules
