import logging
import sys

import p4_changelist_cfg as cfg
import p4_changelist_utils as p4cl_utils
import p4_changelist_ui as p4cl_ui

def view_changelist_archive():
    main_window = p4cl_ui.P4CLMainWindow()

    main_window.start(cfg.arguments.input_path)
