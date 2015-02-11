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

# Pure functions
def create_actions(jail_dir, files, dirs, managed_objects, jail_stuct):

    reduntant_files = diff(files + dirs, managed_objects)
    rm_actions = map(create_rm_action, reduntant_files)


    return rm_actions

def is_file(jail_struct):
    def _is_file(file_path):
        pass
    return _is_file

def is_dir(jail_struct):
    def _is_dir(dir_path):
        pass
    return _is_dir

def diff(a, b):
    return [x for x in a if x not in b]

def create_rm_action(f):
    def _rm_action():
        pass
    return (_rm_action, "rm {0}".format(f))

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
        jail_struct = get_jail_struct(args['jail_dir'])

        # Pure functional
        actions = create_actions(args['jail_dir'], files, dirs, managed_objects, jail_struct)

        # Take actions
        msg = reduce(create_msg, map(take_action, actions), {changed = False})

    else:
        msg = destoy_jail(args['jail_dir'], MEMORY_FILE)
        module.exit_json(msg)

from ansible.module_utils.basic import *
main()
