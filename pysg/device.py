from . import sg_pt, Buffer, sg_cmds
from .sense import Sense
from .cmd import Command
from .enum import DoPTResult, StatusCodes, PTResult, ErrorCategories, PTFlags
from typing import Optional, Dict
from weakref import WeakValueDictionary
from functools import wraps


class SCSIError(RuntimeError):
    def __init__(self, status_code: StatusCodes, message: str, *args):
        msg = "[SCSI Status {}] {}".format(status_code, message)
        super().__init__(msg, *args)
        self.status_code = status_code


class CheckConditionError(SCSIError):
    def __init__(self, sense: Sense, message: str, *args):
        super().__init__(StatusCodes.CHECK_CONDITION,
                         sense.to_str(message),
                         *args)
        self.sense = sense


class SGCMDSError(RuntimeError):
    def __init__(self, error_category: ErrorCategories, message: str, *args):
        msg = "[Error {}] {}".format(error_category, message)
        super().__init__(msg, *args)
        self.error_category = error_category


class PTObject(object):
    _objects = WeakValueDictionary()

    def __init__(self,
                 cmd: Command,
                 sense_size: int=32,
                 data_in: Optional[Buffer]=None,
                 data_out: Optional[Buffer]=None,
                 packet_id: Optional[int]=None,
                 tag: Optional[int]=None,
                 task_management: Optional[int]=None,
                 task_attrs: Optional[Dict[int, int]]=None,
                 flags: Optional[PTFlags]=None):
        self._objects[id(self)] = self

        self._obj = sg_pt.lib.construct_scsi_pt_obj()

        self._sense = Sense(size=sense_size)
        self._data_in = data_in
        self._data_out = data_out
        if task_attrs is None:
            task_attrs = {}
        self.task_attrs = task_attrs

        self.cmd = cmd
        self.packet_id = packet_id
        self.tag = tag
        self.task_management = task_management

        ffi = sg_pt.ffi
        lib = sg_pt.lib
        lib.set_scsi_pt_cdb(self._obj,
                            ffi.cast('unsigned char *', self.cmd._cdb), len(self.cmd))
        lib.set_scsi_pt_sense(self._obj, self._sense.ptr, len(self._sense))
        if self._data_in is not None:
            lib.set_scsi_pt_data_in(self._obj, self._data_in.ptr,
                                    len(self._data_in.ptr))
        if self._data_out is not None:
            lib.set_scsi_pt_data_out(self._obj, self._data_out.ptr,
                                     len(self._data_out.ptr))
        if self.packet_id is not None:
            lib.set_scsi_pt_packet_id(self._obj, self.packet_id)
        if self.tag is not None:
            lib.set_scsi_pt_tag(self._obj, self.tag)
        if self.task_management is not None:
            lib.set_scsi_pt_task_management(self._obj, self.task_management)
        for k, v in self.task_attrs.items():
            lib.set_scsi_pt_task_attr(self._obj, k, v)
        if flags is not None:
            lib.set_scsi_pt_flags(self._obj, flags)

    def __repr__(self):
        if self._data_in is not None:
            return "<{}.{}: {} w/ {} bytes read>".format(
                    self.__class__.__module__,
                    self.__class__.__name__,
                    str(self.cmd),
                    len(self._data_in))
        elif self._data_out is not None:
            return "<{}.{}: {} w/ {} bytes write>".format(
                    self.__class__.__module__,
                    self.__class__.__name__,
                    str(self.cmd),
                    len(self._data_out))
        else:
            return "<{}.{}: {} w/o data>".format(
                    self.__class__.__module__,
                    self.__class__.__name__,
                    str(self.cmd))

    @property
    def sense(self) -> Sense:
        return self._sense

    @property
    def sense_size(self) -> int:
        return sg_pt.lib.get_scsi_pt_sense_len(self._obj)

    @property
    def data(self) -> Buffer:
        if self._data_in is not None:
            return self._data_in
        elif self._data_out is not None:
            return self._data_out
        else:
            return None

    @property
    def result_category(self) -> PTResult:
        return PTResult(sg_pt.lib.get_scsi_pt_result_category(self._obj))

    @property
    def resid(self) -> int:
        return sg_pt.lib.get_scsi_pt_resid(self._obj)

    @property
    def status_response(self) -> StatusCodes:
        return StatusCodes(
                sg_pt.lib.get_scsi_pt_status_response(self._obj))

    @property
    def os_err(self) -> int:
        return sg_pt.lib.get_scsi_pt_os_err(self._obj)

    @property
    def transport_err(self) -> int:
        return sg_pt.lib.get_scsi_pt_transport_err(self._obj)

    @property
    def transport_err_str(self) -> str:
        buf = sg_pt.ffi.new('char[512]')
        sg_pt.lib.get_scsi_pt_transport_err_str(self._obj, 512, buf)
        return sg_pt.ffi.string(buf).decode('utf-8')

    @property
    def duration_ms(self) -> int:
        return sg_pt.lib.get_scsi_pt_duration_ms(self._obj)

    def __del__(self):
        sg_pt.lib.destruct_scsi_pt_obj(self._obj)

    def do_scsi_pt(self, device: 'Device', timeout: int=0,
                   noisy: bool=True, verbose: bool=True):
        ret = sg_pt.lib.do_scsi_pt(self._obj, device.fileno(),
                                     timeout, 1 if verbose else 0)

        sg_cmds.lib.sg_cmds_process_resp(
                sg_cmds.ffi.cast('struct sg_pt_base *', self._obj),
                self.cmd.name.encode('utf-8'),
                ret, len(self.data), self._sense.ptr,
                1 if noisy else 0,
                1 if verbose else 0,
                sg_cmds.ffi.NULL)

        if ret is DoPTResult.BAD_PARAMS:
            raise ValueError("Parameter is not set properly")
        elif ret is DoPTResult.TIMEOUT:
            raise OSError(errno.ETIMEDOUT, "SCSI PT Timed out")
        if self.result_category is PTResult.TRANSPORT_ERR:
            raise RuntimeError("Transport Error[{}]: {}".format(
                hex(self.transport_err, self.transport_err_str)))
        elif self.result_category is PTResult.OS_ERR:
            raise OSError(self.os_err, "SCSI PT Failed")
        elif self.result_category is PTResult.STATUS:
            raise SCSIError(self.status_response, "{} failed".format(self.cmd))
        elif self.result_category is PTResult.SENSE:
            raise CheckConditionError(self.sense, "{} failed".format(self.cmd),
                                      self.data)


class BareDevice(object):
    _context = []

    @classmethod
    def current(cls) -> Optional['Device']:
        if cls._context:
            return cls._context[-1]
        else:
            return None

    def __init__(self, path: str, readonly: bool=False, verbose: bool=True, *,
                 flags: Optional[int]=None):
        self._depth = 0
        self.timeout = 5
        self.verbose = verbose
        if flags is not None:
            self._fd = sg_pt.lib.scsi_pt_open_flags(path.encode('utf-8'),
                                                    flags,
                                                    1 if verbose else 0)
        else:
            self._fd = sg_pt.lib.scsi_pt_open_device(path.encode('utf-8'),
                                                     1 if readonly else 0,
                                                     1 if verbose else 0)

        if self._fd < 0:
            raise OSError(-self._fd, "Can't open device {}".format(path))

    def close(self):
        if self._fd is not None:
            sg_pt.lib.scsi_pt_close_device(self._fd)
            self._fd = None
        return self

    def fileno(self):
        return self._fd

    def __enter__(self):
        self._depth += 1
        self._context.append(self)

    def __exit__(self, exc_type, value, tb):
        if self._context[-1] is self:
            self._context.pop()

        if self._depth <= 0:
            return
        self._depth -= 1
        if self._depth == 0:
            self.close()

    @wraps(PTObject)
    def command(self, *args, **kwargs):
        obj = PTObject(*args, **kwargs)
        obj.do_scsi_pt(self, self.timeout, self.verbose)
        return obj


def cmds_mixin(cls):
    for k in dir(sg_cmds.lib):
        if k.startswith('sg_') and not k.startswith('sg_cmds_'):
            f = getattr(sg_cmds.lib, k)

            def gen_helper(fn):
                @wraps(fn)
                def helper(self, *args, **kwargs):
                    ret = fn(self.fileno(), *args, **kwargs)
                    if ret < 0:
                        raise RuntimeError("{} failed".format(k))
                    elif ret != 0:
                        raise SGCMDSError(ErrorCategories(ret))
                return helper

            setattr(cls, k[3:], gen_helper(f))
    return cls


@cmds_mixin
class Device(BareDevice):
    
    pass

