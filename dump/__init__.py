import os
import sys
import logging
import re
import difflib

import p4_changelist_cfg as cfg
import p4_changelist_utils as p4cl_utils
import p4

import marshal
import io
import zipfile
import datetime
from dateutil.tz import tzlocal


def dump_changelist():
    logging.debug('dump change list:%s', cfg.arguments.p4_changelist)
    logging.debug('with arguments:{}'.format(cfg.arguments))

    if cfg.arguments.p4_changelist == 'default' and cfg.arguments.use_shelved:
        logging.error("default change list does not have shelved files");
        sys.exit(1)

    archive_path = __get_archive_path()

    try:
        with zipfile.ZipFile(archive_path, 'w') as zip_archive:
            __dump_changelist(zip_archive)
    except:
        os.remove(archive_path)
        raise

def __dump_changelist(zip_archive):
    workspace = p4cl_utils.get_workspace()

    logging.debug('process root %s for client %s', workspace.root, cfg.arguments.p4_client)

    if cfg.arguments.p4_changelist == 'default':
        opened_files = p4cl_utils.unmarshal_result(p4.run_p4(['opened', '-c', cfg.arguments.p4_changelist]).stdout)

        if len(opened_files) > 0:
            __dump_opened_files(zip_archive, workspace, opened_files)
        else:
            logging.info("no file to dump for default change list");
    else:
        if not cfg.arguments.use_shelved:
            opened_files = p4cl_utils.unmarshal_result(p4.run_p4(['opened', '-c', cfg.arguments.p4_changelist]).stdout)

            if len(opened_files) > 0:
                __dump_changelist_desription(zip_archive, False)
                __dump_opened_files(zip_archive, workspace, opened_files)
            else:
                logging.info("no opened file to dump for change list:%s", cfg.arguments.p4_changelist);

        # try shelved files
        if cfg.arguments.use_shelved or len(opened_files) == 0:
            __dump_changelist_desription(zip_archive, True)

            logging.debug("process shelved files for changelist:%s", cfg.arguments.p4_changelist)
            opened_files = p4cl_utils.unmarshal_result(p4.run_p4(['describe',
                                                         '-s',
                                                         '-S',
                                                         cfg.arguments.p4_changelist
                                                         ]).stdout)

            if b'depotFile0' in opened_files[0]:
                __dump_describe_files(zip_archive, workspace, opened_files[0])
            else:
                logging.info("no shelved file to dump for changelist:%s", cfg.arguments.p4_changelist)

def __get_archive_path():
    return os.path.join(cfg.arguments.output_dir,
                        cfg.arguments.output_file if cfg.arguments.output_file else (cfg.arguments.p4_changelist + ".zip"))

def __dump_opened_files(zip_archive, client_workspace, opened_files):
    client_root = client_workspace.root

    for opened_file in opened_files:
        if not b'action' in opened_file:
            logging.warn("opened file without action found:%s", opened_file)
            continue

        logging.debug("process opened file:%s", opened_file)

        if opened_file[b'action'] == b'add':
            __dump_opened_files_added(zip_archive,
                                      opened_file[b'depotFile'].decode('utf-8'),
                                      p4cl_utils.get_client_file(client_root,
                                                        opened_file[b'clientFile'].decode('utf-8')))
        else:
            __dump_opened_files_diff(zip_archive,
                                     opened_file[b'depotFile'].decode('utf-8'),
                                     opened_file[b'haveRev'].decode('utf-8'),
                                     p4cl_utils.get_client_file(client_root,
                                                       opened_file[b'clientFile'].decode('utf-8')))

def __dump_opened_files_added(zip_archive, depot_file, client_files):
    client_file, file_name = client_files

    # save source revision
    with zip_archive.open(file_name, 'w') as z_file:
        z_file.write(b'')

    f_time = datetime.datetime.strftime(datetime.datetime.now(tzlocal()),
                                        "%Y-%m-%d %H:%M:%S.%f %z")
    # save diff
    with zip_archive.open(file_name + '.patch', 'w') as z_file:
        with open(client_file) as f:
            content = f.readlines()

            diff_content = difflib.unified_diff('',
                                                content,
                                                file_name,
                                                file_name,
                                                f_time,
                                                f_time
                                                )
            z_file.writelines(map(lambda line:line.encode('utf-8', 'surrogateescape'), diff_content))

def __dump_opened_files_diff(zip_archive, depot_file, depot_have_rev, client_files):
    client_file, file_name = client_files

    # save source revision
    source_content = __p4_print_file_content(depot_file + "#" + depot_have_rev)
    with zip_archive.open(file_name, 'w') as z_file:
        z_file.write(source_content)

    # save the diff file
    diff_content = p4.run_p4(['diff', '-du3', '-f', '-Od', '-t', depot_file], False).stdout
    # normalize the diff
    contents = []

    with zip_archive.open(file_name + ".patch", 'w') as z_file:
        z_file.write(__get_diff_header(file_name))

        with io.BytesIO(diff_content) as f:
            line = f.readline()

            while line:
                if not (line.startswith(b'--- ') or line.startswith(b'+++ ')):
                    z_file.write(line)

                line = f.readline()


def __dump_describe_files(zip_archive, client_workspace, describe_file):
    file_index = 0

    #find out added files
    added_files = []

    while True:
        depot_file = bytes('depotFile{}'.format(file_index), 'utf-8')
        action = bytes('action{}'.format(file_index), 'utf-8')

        if not (depot_file in describe_file and action in describe_file):
            break

        if describe_file[action] == b'add':
            added_files.append(describe_file[depot_file])
        file_index += 1

    # process added files
    if len(added_files) > 0:
        for added_file in added_files:
            __dump_describe_added_file(zip_archive, client_workspace, added_file)

    # dump edit files
    diff_content = p4.run_p4(['describe', '-du3', '-S', cfg.arguments.p4_changelist], False).stdout
    __save_diff_content(zip_archive, client_workspace, diff_content)

def __save_diff_content(zip_archive, client_workspace, diff_content):
    z_file = None
    view_map = client_workspace.view_map

    with io.BytesIO(diff_content) as f:
        line = f.readline()

        while line:
            if line.startswith(b'==== //depot/'):
                # skip empty line
                f.readline()

                line = line.decode('utf-8')
                file_name = p4cl_utils.get_view_mapped_file_name(view_map, line)

                if z_file:
                    z_file.close()

                # save the source revision file
                depot_file_with_rev = line[len('==== ') : line.index(' (')]
                with zip_archive.open(file_name, 'w') as z_file:
                    file_content = __p4_print_file_content(depot_file_with_rev)
                    z_file.write(file_content)

                # open patch file
                z_file = zip_archive.open(file_name + ".patch", 'w')

                z_file.write(__get_diff_header(file_name))
            elif z_file:
                z_file.write(line)

            line = f.readline()

def __dump_describe_added_file(zip_archive, client_workspace, added_file):
    view_map = client_workspace.view_map

    added_file = added_file.decode('utf-8')
    depot_file_with_rev = ''.join([added_file, '@=', cfg.arguments.p4_changelist])
    file_content = __p4_print_file_content(depot_file_with_rev)
    file_content = [x + '\n' for x in file_content.decode('utf-8', 'surrogateescape').splitlines()]

    file_name = p4cl_utils.get_view_mapped_file_name(view_map, added_file)

    # save source revision
    with zip_archive.open(file_name, 'w') as z_file:
        z_file.write(b'')

    f_time = datetime.datetime.strftime(datetime.datetime.now(tzlocal()),
                                        "%Y-%m-%d %H:%M:%S.%f %z")
    # save new file as diff
    with zip_archive.open(file_name + ".patch", 'w') as z_file:
        diff_content = difflib.unified_diff('',
                                            file_content,
                                            file_name,
                                            file_name,
                                            f_time,
                                            f_time
                                            )
        z_file.writelines(map(lambda line:line.encode('utf-8', 'surrogateescape'), diff_content))

def __dump_changelist_desription(zip_archive, use_shelved):
    content = p4.run_p4(['describe',
                         '-s',
                         '-S' if use_shelved else '',
                         cfg.arguments.p4_changelist
                         ], False).stdout

    file_name = '{}_description.txt'.format(cfg.arguments.p4_changelist)

    with zip_archive.open(file_name, 'w') as z_file:
        z_file.write(content)

def __get_diff_header(file_name):
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

    return bytearray(''.join(contents), 'utf-8')

def __p4_print_file_content(file_name):
    source_content = p4.run_p4(['print', file_name], False).stdout

    with io.BytesIO(source_content) as f:
        with io.BytesIO() as d:
            d.writelines(f.readlines()[1:])
            return d.getvalue()
