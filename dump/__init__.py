import logging

import p4_changelist_cfg as cfg

def dump_changelist():
    logging.debug('dump change list:%d', cfg.verbose)
    logging.debug('with arguments:{}'.format(cfg.arguments))
