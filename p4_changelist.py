import os
import argparse
import sys
import logging
import json

sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

import p4_changelist_cfg as cfg


def args_parser():
    parser = argparse.ArgumentParser(prog='p4-changelist',
                                     description='program to dump p4 change list as archive and apply archived file to p4, view the archived change list')
    parser.add_argument('-c', '--p4-client', type=str, help='p4 client to use, will use $P4CLIENT if not present', required=False)
    parser.add_argument('-p', '--p4-port', type=str, help='p4 port to use, will use $P4PORT if not present', required=False)
    parser.add_argument('-H', '--p4-host', type=str, help='p4 host to use, will use $P4HOST if not present', required=False)
    parser.add_argument('-u', '--p4-user', type=str, help='p4 user to use, will use $P4USER if not present', required=False)
    parser.add_argument('-P', '--p4-passwd', type=str, help='p4 password to use, will use $P4PASSWD if not present', required=False)
    parser.add_argument('--p4-bin', type=str, help='p4 binary to run with, will use p4(.exe) from $PATH if not present', required=False)
    parser.add_argument('--timeout', type=int, help='timeout value for all p4 command, default will be 30 seconds', required=False, default=30)
    parser.add_argument('-v', '--verbose', action='count', help='print debug information', required=False, default=0)

    sub_parsers = parser.add_subparsers(dest='command')
    sub_parsers.required = True

    dump_parser = sub_parsers.add_parser('dump', help='dump p4 change list')
    dump_parser.add_argument('-C', '--p4-changelist', type=str, help='p4 change list to dump', required=False, default='default')
    dump_parser.add_argument('-d', '--output-dir', type=str, help='dump change list to directory, default to current directory', required=False, default='.')
    dump_parser.add_argument('--use-shelved', action='store_true', help='dump change list shelved version', required=False)
    dump_parser.add_argument('-o', '--output-file', type=str, help='dump change list archive file name, default will be <change list number>.p4c', required=False)

    apply_parser = sub_parsers.add_parser('apply', help='apply p4 change list')
    apply_parser.add_argument('-i', '--input-path', type=str, help='change list archive file path', required=True)

    view_parser = sub_parsers.add_parser('view', help='view p4 change list')
    view_parser.add_argument('-i', '--input-path', type=str, help='change list archive file path', required=True)
    return parser

if __name__ == '__main__':
    parser = args_parser().parse_args()

    cfg.verbose = parser.verbose
    cfg.arguments = parser

    if parser.verbose >= 1:
        logging.getLogger('').setLevel(logging.DEBUG)

    logging.debug('running command:%s', parser.command)

    if parser.command == 'apply':
        from apply import apply_changelist
        apply_changelist()
    elif parser.command == 'dump':
        from dump import dump_changelist
        dump_changelist()
    else:
        from view import view_changelist_archive
        view_changelist_archive()
