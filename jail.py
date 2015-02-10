#!/usr/bin/env python

DOCUMENTATION = '''
---
module: jail
short_description: creates chrooted jail folder
description:
    - Creates custom chrooted jail folder
options:
    state:
        description:
            - Folder absent or present
        required: false
        default: present
        choices: [
            "present", "absent"
        ]
        aliases: []
    jail_folder:
        description:
            - chroot folder
        required: true
        default: null
    commands:
        description:
            - what command should be available in jail
        required: false
        default: null
    other:
        description:
            - what else should be copied
        required: false
        default: null
'''
import os
import os.path
import shutil
import subprocess
import re
import itertools

MEMORY_FILE = '/var/ansible-jail.mem'

def is_file_present(root = '/'):
    def _is_file_present(path):
        return os.path.isfile(path)
    return _is_file_present

def get_arguments(module):
    args = {}
    args['state'] = module.params['state']
    args['jail_folder'] = module.params['jail_folder']
    args['commands'] = module.params['commands'] or []
    args['other'] = module.params['other'] or []
    return args

def get_copy_to_jail_func(jail_folder):
    def _copy_to_jail(file_path):
        full_file_path = os.path.join(jail_folder, file_path[1:])
        dir_path = os.path.dirname(full_file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        shutil.copy2(file_path, full_file_path)
    return _copy_to_jail

def get_library_dependencies(command):
    ldd_out = subprocess.check_output(['ldd', command])
    deps = []
    for line in ldd_out.splitlines():
        match = re.match(r'\t.* => (.*) \(0x', line)
        if match:
            deps.append(match.group(1))
    return deps

def remove_file(path):
    os.remove(path)

def get_old_files(memory_file):
    if not os.path.isfile(memory_file):
        return []
    with open(memory_file, 'r') as f:
        files = f.read().splitlines()
    return files

def save_managed_files(files, memory_file):
    with open(memory_file, 'w') as f:
        f.writelines(["{0}\n".format(x) for x in files if x != ''])

def diff(a, b):
    return [x for x in a if x not in b]

def main():
    arguments = {
        'state': {
            'required'  : False,
            'choises'   : ['present', 'absent'],
            'default'   : 'present',
        },
        'jail_folder'   : { 'required': True, 'default': None },
        'commands'      : { 'default': None },
        'other'         : { 'default': None },
    }
    module = AnsibleModule(argument_spec = arguments)
    args = get_arguments(module)

    if args['state'] == 'present':
        # Get copy fuction
        copy_func = get_copy_to_jail_func(args['jail_folder'])

        # Get all library dependencies that all the commands have
        libs = sum(map(get_library_dependencies, args['commands']), [])

        managed_files = libs + args['commands'] + args['other']

        old_files = get_old_files(MEMORY_FILE)

        reduntant_files = diff(old_files, managed_files)

        # Filter out the files that have already been copied
        files = itertools.ifilter(is_file_present(args['jail_folder']), managed_files)

        map(copy_func, files)
        map(remove_file, reduntant_files)

        save_managed_files(managed_files, MEMORY_FILE)

    else:
        pass

    module.exit_json(changed = True, msg = "SUCCESS")

from ansible.module_utils.basic import *
main()
