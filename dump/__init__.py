import sys
import logging

import p4_changelist_cfg as cfg
import p4

import marshal
import io


def __unmarshal_result(data):
    results = []

    with io.BytesIO(data) as f:
        try:
            while True:
                results.append(marshal.load(f))
        except:
            pass

    return results

def __dump_opened_files(opened_files):
    edit_files = []
    add_files = []

    for opened_file in opened_files:
        if not b'action' in opened_file:
            logging.warn("opened file without action found:%s", opened_file)
            continue

        logging.debug("process opened file:%s", opened_file)

        if opened_file[b'action'] == b'add':
            __dump_opened_files_added(opened_file)
        else:
            __dump_opened_files_diff(opened_file)

def __dump_describe_files(describe_file):
    pass

def dump_changelist():
    logging.debug('dump change list:%s', cfg.arguments.p4_changelist)
    logging.debug('with arguments:{}'.format(cfg.arguments))

    if cfg.arguments.p4_changelist == 'default' and cfg.arguments.use_shelved:
        logging.error("default change list does not have shelved files");
        sys.exit(1)

    if cfg.arguments.p4_changelist == 'default':
        opened_files = __unmarshal_result(p4.run_p4(['opened', '-c', cfg.arguments.p4_changelist]).stdout)

        if len(opened_files) > 0:
            __dump_opened_files(opened_files)
        else:
            logging.info("no file to dump for default change list");
    else:
        if not cfg.arguments.use_shelved:
            opened_files = __unmarshal_result(p4.run_p4(['describe', cfg.arguments.p4_changelist]).stdout)

        # try shelved files, the first object is
        if cfg.arguments.use_shelved or (not b'depotFile0' in opened_files[0] and b'shelved' in opened_files[0]):
            logging.debug("process shelved files for changelist:%s", cfg.arguments.p4_changelist)
            opened_files = __unmarshal_result(p4.run_p4(['describe',
                                                         '-du3',
                                                         '-S',
                                                         cfg.arguments.p4_changelist
                                                         ]).stdout)

        if b'depotFile0' in opened_files[0]:
            __dump_describe_files(opened_files[0])
        else:
            logging.info("no file to dump for changelist:%s", cfg.arguments.p4_changelist)
