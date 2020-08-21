import logging

import p4_changelist_cfg as cfg

def apply_changelist():
    logging.debug('apply change list:%d', cfg.verbose)
    logging.debug('with arguments:{}'.format(cfg.arguments))
