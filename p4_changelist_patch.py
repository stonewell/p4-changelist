import io
import logging

from python_patch.patch import Patch as PPatch
from python_patch.patch import fromstring


def apply_to_content(origin_content, diff_content):
    ps = fromstring(diff_content)

    if not ps:
        logging.error("unable to load diff_content:%s", diff_content)
        raise (None, 1)

    p = ps.items[0]

    with io.BytesIO() as new_stream:
        with io.BytesIO(origin_content) as origin_stream:
            patched_stream = ps.patch_stream(origin_stream, p.hunks)
            new_stream.writelines(patched_stream)
        return (new_stream.getvalue(), 0)
