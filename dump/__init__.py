import os
import sys
import logging

import p4_changelist_cfg as cfg
import p4

import marshal
import io
import zipfile
import datetime
from dateutil.tz import tzlocal


def __unmarshal_result(data):
    results = []

    with io.BytesIO(data) as f:
        try:
            while True:
                results.append(marshal.load(f))
        except:
            pass

    return results

def dump_changelist():
    logging.debug('dump change list:%s', cfg.arguments.p4_changelist)
    logging.debug('with arguments:{}'.format(cfg.arguments))

    if cfg.arguments.p4_changelist == 'default' and cfg.arguments.use_shelved:
        logging.error("default change list does not have shelved files");
        sys.exit(1)

    archive_path = __get_archive_path()

    with zipfile.ZipFile(archive_path, 'w') as zip_archive:
        __dump_changelist(zip_archive)

def __dump_changelist(zip_archive):
    # get workspace root
    workspace = __unmarshal_result(p4.run_p4(['client', '-o', cfg.arguments.p4_client]).stdout)

    if len(workspace) < 1:
        logging.error('unknown p4 client:%s', cfg.arguments.p4_client)
        sys.exit(2)

    if not b'Root' in workspace[0]:
        logging.error('unknown root for p4 client:%s', cfg.arguments.p4_client)
        sys.exit(3)

    root = workspace[0][b'Root'].decode('utf-8')

    logging.debug('process root %s for client %s', root, cfg.arguments.p4_client)

    if cfg.arguments.p4_changelist == 'default':
        opened_files = __unmarshal_result(p4.run_p4(['opened', '-c', cfg.arguments.p4_changelist]).stdout)

        if len(opened_files) > 0:
            __dump_opened_files(zip_archive, root, opened_files)
        else:
            logging.info("no file to dump for default change list");
    else:
        if not cfg.arguments.use_shelved:
            opened_files = __unmarshal_result(p4.run_p4(['opened', '-c', cfg.arguments.p4_changelist]).stdout)

            if len(opened_files) > 0:
                __dump_opened_files(zip_archive, root, opened_files)
            else:
                logging.info("no file to dump for change list:%s", cfg.arguments.p4_changelist);

        # try shelved files
        if cfg.arguments.use_shelved or len(opened_files) == 0:
            logging.debug("process shelved files for changelist:%s", cfg.arguments.p4_changelist)
            opened_files = __unmarshal_result(p4.run_p4(['describe',
                                                         '-s',
                                                         '-S',
                                                         cfg.arguments.p4_changelist
                                                         ]).stdout)

            if b'depotFile0' in opened_files[0]:
                __dump_describe_files(zip_archive, root, opened_files[0])
            else:
                logging.info("no file to dump for changelist:%s", cfg.arguments.p4_changelist)

def __get_archive_path():
    return os.path.join(cfg.arguments.output_dir,
                        cfg.arguments.output_file if cfg.arguments.output_file else (cfg.arguments.p4_changelist + ".zip"))

def __dump_opened_files(zip_archive, client_root, opened_files):
    for opened_file in opened_files:
        if not b'action' in opened_file:
            logging.warn("opened file without action found:%s", opened_file)
            continue

        logging.debug("process opened file:%s", opened_file)

        if opened_file[b'action'] == b'add':
            __dump_opened_files_added(zip_archive,
                                      opened_file[b'depotFile'].decode('utf-8'),
                                      __get_client_file(client_root,
                                                        opened_file[b'clientFile'].decode('utf-8')))
        else:
            __dump_opened_files_diff(zip_archive,
                                     opened_file[b'depotFile'].decode('utf-8'),
                                     __get_client_file(client_root,
                                                       opened_file[b'clientFile'].decode('utf-8')))

def __get_client_file(client_root, client_file):
    pattern = ''.join(['//', cfg.arguments.p4_client, '/'])

    return (client_file.replace(pattern, ''.join([client_root, '/'])),
            client_file.replace(pattern, ''))

def __dump_opened_files_added(zip_archive, depot_file, client_files):
    client_file, file_name = client_files

    with zip_archive.open(file_name, 'w') as z_file:
        z_file.write(bytearray(''.join(['--- ', file_name, ' ',
                                        datetime.datetime.strftime(datetime.datetime.now(tzlocal()),
                                                                   "%Y-%m-%d %H:%M:%S.%f %z"),
                                        '\n']),
                               'utf-8'))
        z_file.write(bytearray(''.join(['+++ ', file_name, ' ',
                                        datetime.datetime.strftime(datetime.datetime.now(tzlocal()),
                                                                   "%Y-%m-%d %H:%M:%S.%f %z"),
                                        '\n']),
                               'utf-8'))

        with open(client_file) as f:
            line = f.readline()

            while line:
                z_file.write(bytearray(''.join(['+ ', line]), 'utf-8'))
                line = f.readline()

def __dump_opened_files_diff(zip_archive, depot_file, client_files):
    diff_content = p4.run_p4(['diff', '-du3', '-f', '-Od', '-t', depot_file], False).stdout
    client_file, file_name = client_files

    # normalize the diff
    contents = [
        ''.join(['--- ', file_name, ' ',
                 datetime.datetime.strftime(datetime.datetime.now(tzlocal()),
                                            "%Y-%m-%d %H:%M:%S.%f %z"),
                 '\n']),
        ''.join(['+++ ', file_name, ' ',
                 datetime.datetime.strftime(datetime.datetime.now(tzlocal()),
                                            "%Y-%m-%d %H:%M:%S.%f %z"),
                 '\n'])
    ]

    with io.BytesIO(diff_content) as f:
        line = f.readline().decode('utf-8')

        while line:
            if not (line.startswith('--- ') or line.startswith('+++ ')):
                contents.append(line)

            line = f.readline().decode('utf-8')

    with zip_archive.open(file_name, 'w') as z_file:
        z_file.write(bytearray(''.join(contents), 'utf-8'))

def __dump_describe_files(zip_archive, client_root, describe_file):
    file_index = 0

    #find out added files
    added_files = []

    while True:
        depot_file = 'depotFile{}'.format(file_index)
        action = 'action{}'.format(file_index)

        if not (depot_file in describe_file and action in describe_file):
            break

        added_files.append(describe_file[depot_file])
        file_index += 1

    # process added files
    if len(added_files) > 0:
        for added_file in added_files:
            __dump_describe_added_file(zip_archive, client_root, added_file)

    # dump edit files
    diff_content = p4.run_p4(['describe', '-du3', '-S', cfg.arguments.p4_changelist], False).stdout
    print(diff_content.decode('utf-8'))
