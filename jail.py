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

def is_file(root = '/'):
    def _is_file(path):
        if root != '/':
            path = resolve_jail_path(root)(path)
        return os.path.isfile(path)
    return _is_file

def is_folder(root = '/'):
    def _is_folder(path):
        if root != '/':
            path = resolve_jail_path(root)(path)
        return os.path.isdir(path)
    return _is_folder

def get_arguments(module):
    args = {}
    args['state'] = module.params['state']
    args['jail_folder'] = module.params['jail_folder']
    args['commands'] = module.params['commands'] or []
    args['other'] = module.params['other'] or []
    return args

def copy_file_to_jail(jail_folder):
    def _copy_to_jail(path):
        jail_path = resolve_jail_path(jail_folder)(path)
        jail_dir_path = os.path.dirname(jail_path)
        if not os.path.exists(jail_dir_path):
            os.makedirs(jail_dir_path)
        shutil.copy2(path, jail_path)

    return _copy_to_jail

def copy_folder_to_jail(jail_folder):
    def _copy_folder_to_jail(path):
        jail_path = resolve_jail_path(jail_folder)(path)
        jail_dir_path = os.path.dirname(jail_path)
        if not os.path.exists(jail_dir_path):
            os.makedirs(jail_dir_path)
        shutil.copytree(path, jail_path)

    return _copy_folder_to_jail

def get_library_dependencies(command):
    ldd_out = subprocess.check_output(['ldd', command])
    deps = []
    for line in ldd_out.splitlines():
        match = re.match(r'\t.* => (\S*) \(0x|\t(\/\S*) \(0x', line)
        if match:
            if match.group(1) or match.group(2):
                deps.append(match.group(1) or match.group(2))
    return deps

def remove_file(file_path):
    os.remove(file_path)

def remove_folder(path):
    shutil.rmtree(path)

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

def resolve_jail_path(jail_folder):
    def _resolve_jail_path(file_path):
        return os.path.join(jail_folder, file_path[1:])
    return _resolve_jail_path

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
        # Get all library dependencies that all the commands have
        libs = sum(map(get_library_dependencies, args['commands']), [])

        managed_files = libs + args['commands'] + args['other']

        #module.exit_json(msg = managed_files)

        old_files = get_old_files(MEMORY_FILE)

        _resolve_jail_path = resolve_jail_path(args['jail_folder'])

        reduntant_files = map(_resolve_jail_path, diff(old_files, managed_files))

        # Filter out the files and folders that have already been copied
        files = itertools.ifilterfalse(is_file(args['jail_folder']), itertools.ifilter(is_file('/'), managed_files))
        folders = itertools.ifilterfalse(is_folder(args['jail_folder']), itertools.ifilter(is_folder('/'), managed_files))

        map(copy_file_to_jail(args['jail_folder']), files)
        map(copy_folder_to_jail(args['jail_folder']), folders)
        map(remove_file, itertools.ifilter(is_file(), reduntant_files))
        map(remove_folder, itertools.ifilter(is_folder(), reduntant_files))

        save_managed_files(managed_files, MEMORY_FILE)

    else:
        if os.path.isdir(args['jail_folder']):
            shutil.rmtree(args['jail_folder'])
        if os.path.isfile(MEMORY_FILE):
            remove_file(MEMORY_FILE)

    module.exit_json(changed = True, msg = "SUCCESS")

from ansible.module_utils.basic import *
main()
