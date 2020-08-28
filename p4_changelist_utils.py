import p4_changelist_cfg as cfg
import p4

import logging
import marshal
import io
import re


def unmarshal_result(data):
    results = []

    with io.BytesIO(data) as f:
        try:
            while True:
                results.append(marshal.load(f))
        except:
            pass

    return results

class Workspace(object):
    pass

def get_workspace():
    workspace = Workspace()

    # get workspace root
    workspace.raw_data = unmarshal_result(p4.run_p4(['client', '-o', cfg.arguments.p4_client]).stdout)

    if len(workspace.raw_data) < 1:
        logging.error('unknown p4 client:%s', cfg.arguments.p4_client)
        sys.exit(2)

    if not b'Root' in workspace.raw_data[0]:
        logging.error('unknown root for p4 client:%s', cfg.arguments.p4_client)
        sys.exit(3)

    workspace.root = workspace.raw_data[0][b'Root'].decode('utf-8')
    workspace.view_map = __get_view_map(workspace.raw_data[0])

    return workspace

def __get_view_map(workspace):
    view_index = 0

    view_map = {}

    pattern = ''.join(['//', cfg.arguments.p4_client, '/'])

    while True:
        key = bytes('View{}'.format(view_index), 'utf-8')

        if not key in workspace:
            break

        mapping = workspace[key].decode('utf-8')

        parts = mapping.split(pattern)

        if not parts[0].startswith('-'):
            view_map[parts[0].strip()] = parts[1].strip()
        view_index += 1

    return view_map

def get_view_mapped_file_name(view_map, line):
    depot_file = line

    try:
        end = line.index('#')

        depot_file = line[len('==== '):end]
    except:
        pass

    for depot_prefix in view_map:
        if depot_file == depot_prefix:
            return view_map[depot_prefix]

        pattern = depot_prefix.replace('...', '(.*)')
        repl_str = view_map[depot_prefix].replace('...', '\\1')

        if cfg.verbose > 1:
            logging.debug("try replace pattern:%s, for %s", pattern, depot_file)
        file_name, count = re.subn(pattern, repl_str , depot_file, flags=re.IGNORECASE)

        if count > 0:
            logging.debug("try replace pattern:%s, for %s, result:%s", pattern, depot_file, file_name)
            return file_name

    raise ValueError(' '.join([depot_file, 'not found in view map']))

def get_client_file(client_root, client_file):
    pattern = ''.join(['//', cfg.arguments.p4_client, '/'])

    return (client_file.replace(pattern, ''.join([client_root, '/'])),
            client_file.replace(pattern, ''))
