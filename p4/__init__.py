import logging
import subprocess
import sys

import p4_changelist_cfg as cfg


def add_global_args(args):
    if cfg.arguments.p4_client:
        args.extend(['-c', cfg.arguments.p4_client])

    if cfg.arguments.p4_port:
        args.extend(['-p', cfg.arguments.p4_port])

    if cfg.arguments.p4_user:
        args.extend(['-u', cfg.arguments.p4_user])

    if cfg.arguments.p4_host:
        args.extend(['-H', cfg.arguments.p4_host])

    if cfg.arguments.p4_passwd:
        args.extend(['-P', cfg.arguments.p4_passwd])

    args.append('-G')

def run_p4(args):
    cmd_args = []

    #add p4 binary
    if cfg.arguments.p4_bin:
        cmd_args.extend([cfg.arguments.p4_bin])
    else:
        cmd_args.extend(['p4.exe'] if sys.platform == 'win32' else ['p4'])

    add_global_args(cmd_args)
    cmd_args.extend(args)

    subprocess.run(cmd_args)
