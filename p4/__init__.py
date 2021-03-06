import logging
import subprocess
import sys

import p4_changelist_cfg as cfg
import p4_changelist_utils as p4cl_utils


def __add_global_args(args, output_python=True):
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

    # generate python output
    if output_python:
        args.append('-G')

def run_p4(args, output_python=True):
    cmd_args = []

    #add p4 binary
    if cfg.arguments.p4_bin:
        cmd_args.extend([cfg.arguments.p4_bin])
    else:
        cmd_args.extend(['p4.exe'] if sys.platform == 'win32' else ['p4'])

    __add_global_args(cmd_args, output_python)
    cmd_args.extend(args)

    proc = subprocess.run(cmd_args,
                          capture_output=True,
                          timeout=cfg.arguments.timeout)

    if cfg.verbose > 1:
        logging.debug('p4 standard output:[%s]', __get_data(proc.stdout, output_python))

    if proc.stderr:
        logging.error("running p4 get error:%s", __get_data(proc.stderr, output_python))

    if proc.returncode != 0 and proc.stdout:
        logging.error("running p4 get error:%s", __get_data(proc.stdout, output_python))

    proc.check_returncode()

    return proc

def __get_data(data, is_python):
    if is_python:
        unmarshal_data = p4cl_utils.unmarshal_result(data)
        return unmarshal_data[0] if len(unmarshal_data) > 0 else data

    return data.decode('utf-8', errors='ignore')
