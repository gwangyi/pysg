from ._common import aligned_new
from typing import Optional
from . import _pysg, sg_lib
import sys


class Buffer(object):
    signed = False

    def __init__(self, init: Optional[bytes]=None, size=None):
        if self.signed:
            item = 'char'
        else:
            item = 'unsigned char'

        if init is None:
            self._ptr = aligned_new('{}[{}]'.format(item, size))
        else:
            if size is None:
                size = len(init)
            self._ptr = aligned_new('{}[{}]'.format(item, size), init)

    @property
    def ptr(self):
        return self._ptr

    @property
    def buffer(self):
        return _pysg.ffi.buffer(self._ptr)

    def __len__(self):
        return len(self._ptr)


class SignedBuffer(Buffer):
    signed = True


def redirect_output(fd_or_file):
    if hasattr(fd_or_file, 'fileno'):
        fd = fd_or_file.fileno()
    else:
        fd = fd_or_file

    fp = _pysg.lib.fdopen(fd, b'w')
    _pysg.lib.setbuf(fp, _pysg.ffi.NULL)
    sg_lib.lib.sg_set_warnings_strm(fp)

redirect_output(sys.stderr)

