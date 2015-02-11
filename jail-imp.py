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
    args['jail_dir'] = module.params['jail_dir']
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

def get_managed_objects(memory_file):
    if not os.path.isfile(memory_file):
        return []
    with open(memory_file, 'r') as f:
        files = f.read().splitlines()
    return files

def get_jail_tree(jail_dir):
    dir_tree = {}
    # From http://code.activestate.com/recipes/577879-create-a-nested-dictionary-from-oswalk/
    # -------------------------------------------------------------------------
    dir = {}
    jail_dir = jail_dir.rstrip(os.sep)
    start = jail_dir.rfind(os.sep) + 1
    for path, dirs, files in os.walk(jail_dir):
        folders = path[start:].split(os.sep)
        subdir = dict.fromkeys(files)
        parent = reduce(dict.get, folders[:-1], dir)
        parent[folders[-1]] = subdir
    return dir
    # -------------------------------------------------------------------------

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

def take_actions(actions):
    def _take_action(action):
        action[0]()
        return action[1]
    return reduce(create_msg, map(_take_action, actions), {'changed': False, 'msg': []})

def fake_actions(actions):
    def _fake_action(action):
        return action[1]
    return reduce(create_msg, map(_fake_action, actions), {'changed': False, 'msg': []})

def create_msg(msgs, msg):
    msgs['changed'] = True
    msgs['msg'].append(msg)
    return msgs

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

    _missing_files = [x for x in itertools.ifilterfalse(is_file(jail_tree), files)]
    missing_files = remove_duplicates(_missing_files)
    missing_dirs = [x for x in itertools.ifilterfalse(is_dir(jail_tree), dirs)]

    _parent_dirs = map(get_parent_dir_path, missing_files + missing_dirs)
    parent_dirs = remove_duplicates(_parent_dirs)
    missing_parent_dirs = itertools.ifilterfalse(is_dir(jail_tree), parent_dirs)

    path_actions = map(create_make_path_action(jail_dir), missing_parent_dirs)
    file_actions = map(create_cp_file_action(jail_dir), missing_files)
    dir_actions = map(create_cp_dir_action(jail_dir), missing_dirs)

    memory_file_action = [create_memory_file_action(memory_file, missing_files + missing_dirs)]

    return rm_actions + path_actions + file_actions + dir_actions + memory_file_action

def is_file(jail_tree):
    def _is_file(file_path):
        def walker(tree, file_path):
            node = tree.get(file_path[0])
            if len(file_path) == 1:
                if file_path[0] in tree and node == None:
                    return True
                else:
                    return False
            elif node == None:
                return False
            else:
                return walker(node, file_path[1:])
        if jail_tree == {}:
            return False
        else:
            return walker(jail_tree.values()[0] or {}, file_path.split("/")[1:])
    return _is_file

def is_dir(jail_tree):
    def _is_dir(dir_path):
        def walker(tree, dir_path):
            node = tree.get(dir_path[0])
            if node == None:
                return False
            if len(dir_path) == 1:
                return True
            else:
                return walker(node, dir_path[1:])
        if jail_tree == {}:
            return False
        else:
            return walker(jail_tree.values()[0] or {}, dir_path.split("/")[1:])
    return _is_dir

def diff(a, b):
    return [x for x in a if x not in b]

def resolve_jail_path(jail_dir, file_path):
    return os.path.join(jail_dir, file_path[1:])

def get_parent_dir_path(path):
    return "/".join(path.split("/")[:-1])

def remove_duplicates(l):
    return list(set(l))

def create_rm_file_action(jail_dir):
    def _create_rm_file_action(f):
        def _rm_file_action():
            os.remove(resolve_jail_path(jail_dir, f))
        return (_rm_file_action, "rm {0}".format(f))
    return _create_rm_file_action

def create_rm_dir_action(jail_dir):
    def _create_rm_dir_action(d):
        def _rm_dir_action():
            shutil.rmtree(resolve_jail_path(jail_dir, d))
        return (_rm_dir_action, "rm {0}".format(d))
    return _create_rm_dir_action

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
    return (_memory_file_action, "save memory file to {0}".format(memory_file))

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
    module = AnsibleModule(argument_spec = arguments, supports_check_mode = True)
    args = get_arguments(module)

    if args['state'] == 'present':

        # Collect data
        libs = sum(map(get_library_dependencies, args['commands']), [])
        files = libs + args['commands'] + args['other_files']
        dirs = args['dirs']
        managed_objects = get_managed_objects(MEMORY_FILE)
        jail_tree = get_jail_tree(args['jail_dir'])

        # Pure functional
        actions = create_actions(args['jail_dir'], files, dirs, managed_objects, jail_tree, MEMORY_FILE)

        # Take actions
        if not module.check_mode:
            msg = take_actions(actions)
        else:
            msg = fake_actions(actions)
        
        module.exit_json(**msg)

    else:
        msg = destoy_jail(args['jail_dir'], MEMORY_FILE)
        module.exit_json(msg)

from ansible.module_utils.basic import *
main()
