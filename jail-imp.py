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
    jail_dir:
        description:
            - chroot folder
        required: true
        default: null
    commands:
        description:
            - what command should be available in jail
        required: false
        default: null
    other_files:
        description:
            - what else should be copied
        required: false
        default: null
    dirs:
        descritipn:
            - what other directories should be copied
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

# Unpure functions
def get_arguments(module):
    args = {}
    args['state'] = module.params['state']
    args['jail_folder'] = module.params['jail_folder']
    args['commands'] = module.params['commands'] or []
    args['other_files'] = module.params['other_files'] or []
    args['dirs'] = module.params['dirs'] or []
    return args

def get_library_dependencies(command):
    ldd_out = subprocess.check_output(['ldd', command])
    deps = []
    for line in ldd_out.splitlines():
        match = re.match(r'\t.* => (\S*) \(0x|\t(\/\S*) \(0x', line)
        if match:
            if match.group(1) or match.group(2):
                deps.append(match.group(1) or match.group(2))
    return deps

def get_mangaged_objects(memory_file):
    if not os.path.isfile(memory_file):
        return []
    with open(memory_file, 'r') as f:
        files = f.read().splitlines()
    return files

def get_jail_tree(jail_dir):
    dir_tree = {}
    #walker = def walker(node, object_path):
    pass

def destroy_jail(jail_dir, memory_file):
    msg = {}
    msg['changed'] = False
    msg['msg'] = []
    if os.path.isdir(jail_dir):
        shutil.rmtree(jail_dir)
        msg['changed'] = True
        msg['msg'].append("rm {0}".format(jail_dir))
    if os.path.isfile(memory_file):
        remove_file(memory_file)
        msg['changed'] = True
        msg['msg'].append("rm {0}".format(memory_file))
    return msg

def take_action(action):
    pass

def create_msg(msgs, msg):
    return msgs + msg

def save_managed_files(memory_file, files):
    with open(memory_file, 'w') as f:
        f.writelines(["{0}\n".format(x) for x in files if x != ''])

# Pure functions
# -----------------------------------------------------------------------------
def create_actions(jail_dir, files, dirs, managed_objects, jail_tree, memory_file):

    reduntant_objects = diff(files + dirs, managed_objects)
    reduntant_files = itertools.ifilter(is_file(jail_tree), reduntant_objects)
    reduntant_dirs = itertools.ifilter(is_dir(jail_tree), reduntant_objects)

    rm_file_actions = map(create_rm_file_action(jail_dir), reduntant_files)
    rm_dir_actions = map(create_rm_dir_action(jail_dir), reduntant_dirs)
    rm_actions = rm_file_actions + rm_dir_actions

    missing_files = itertools.ifilterfalse(is_file(jail_tree), files)
    missing_dirs = itertools.ifilterfalse(is_dir(jail_tree), dirs)

    parent_dirs = map(lambda x: x.split("/")[:-1], missing_files + missing_folders)
    missing_parent_dirs = itertools.ifilterfalse(is_dir, parent_dirs)
    path_actions = map(create_make_path_action(jail_dir), missing_parent_dirs)

    file_actions = map(create_cp_file_action(jail_dir), missing_files)
    dir_actions = map(create_cp_dir_action(jail_dir), missing_dirs)

    memory_file_action = create_memory_file_action(memory_file, missing_files + missing_dirs)

    return rm_actions + path_actions + file_actions + dir_actions + memory_file_action

def is_file(jail_tree):
    def _is_file(file_path):
        pass
    return _is_file

def is_dir(jail_tree):
    def _is_dir(dir_path):
        pass
    return _is_dir

def diff(a, b):
    return [x for x in a if x not in b]

def resolve_jail_path(jail_dir, file_path):
    return os.path.join(jail_dir, file_path[1:]

def create_rm_file_action(jail_dir):
    def _create_rm_file_action(f):
        def _rm_file_action():
            os.remove(resolve_jail_path(jail_dir, f)
        return (_rm_action, "rm {0}".format(f))
    return _create_rm_action

def create_rm_dir_action(jail_dir):
    def _create_rm_dir_action(d):
        def _rm_dir_action():
            shutil.rmtree(resolve_jail_path(jail_dir, d))
        return (_rm_action, "rm {0}".format(d))
    return _create_rm_action

def create_cp_file_action(jail_dir):
    def _create_cp_file_action(f):
        file_jail_path = resolve_jail_path(jail_dir, f)
        def _cp_file_action():
            shutil.copy2(f, file_jail_path)
        return (_cp_file_action, "cp {0} {1}".format(f, file_jail_path))
    return _create_cp_file_action

def create_cp_dir_action(jail_dir):
    def _create_cp_dir_action(d):
        dir_jail_path = resolve_jail_path(jail_dir, d)
        def _cp_dir_action():
            shutil.copytree(path, jail_path)
        return (_cp_dir_action, "cp {0} {1}".format(d, dir_jail_path))
    return _create_cp_dir_action

def create_make_path_action(jail_dir):
    def _create_make_path_action(path):
        def _make_path_action():
            os.makedirs(resolve_jail_path(jail_dir, path))
        return (_make_path_action, "mkdir {0}".format(path))
    return _create_make_path_action

def create_memory_file_action(memory_file, files):
    def _memory_file_action():
        save_managed_files(memory_file, files)
    return _memory_file_action

# -----------------------------------------------------------------------------

def main():
    arguments = {
        'state': {
            'required'  : False,
            'choises'   : ['present', 'absent'],
            'default'   : 'present',
        },
        'jail_dir'      : { 'required': True, 'default': None },
        'dirs'          : { 'default': None },
        'commands'      : { 'default': None },
        'other_files'   : { 'default': None },
    }
    module = AnsibleModule(argument_spec = arguments)
    args = get_arguments(module)

    if args['state'] == 'present':

        # Collect data
        libs = sum(map(get_library_dependencies, args['commands']), [])
        files = libs + args['commands'] + args['other_files']
        dirs = args['dirs']
        managed_objects = get_managed_objects(MEMORY_FILE)
        jail_tree = get_jail_struct(args['jail_dir'])

        # Pure functional
        actions = create_actions(args['jail_dir'], files, dirs, managed_objects, jail_tree)

        # Take actions
        msg = reduce(create_msg, map(take_action, actions), {changed = False})

    else:
        msg = destoy_jail(args['jail_dir'], MEMORY_FILE)
        module.exit_json(msg)

from ansible.module_utils.basic import *
main()
