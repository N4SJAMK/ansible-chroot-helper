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
    root_folder:
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

def get_arguments():
    pass

def get_copy_to_jail_func(root_folder):
    def _copy_to_jail(path):
        pass
    return _copy_to_jail

def get_library_dependencies(command):
    pass

def remove():
    pass

def main():
    arguments = {
        'state': {
            'required'  : False,
            'choises'   : ['present', 'absent']
            'default'   : 'present',
        },
        'root_folder'   : { 'required': True, 'default': None },
        'commands'      : { 'default': None },
        'other'         : { 'default': None },
    }
    module = AnsibleModule(argument_spec = arguments)
    args = get_arguments(module)

    copy_func = get_copy_to_jail_func(args['root_folder'])

    libs = sum(map(get_library_dependencies, args['commands']), [])
    map(copy_func, libs + args['commands'])
    map(copy_func, args['other'])

from ansible.module_utils.basic import *
main()
