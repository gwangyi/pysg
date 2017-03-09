from . import sg_lib, Buffer
from .enum import SenseKeyCodes
from ._common import HexValueEnum
from collections import namedtuple
from typing import Union
import enum


SenseHeader = namedtuple('SenseHeader',
        ['response_code', 'sense_key', 'asc', 'ascq',
         'byte4', 'byte5', 'byte6', 'additional_length'])


class DescriptorTypes(int, HexValueEnum):
    def __str__(self):
        if self.value == 0x00:
            return "Information"
        elif self.value == 0x01:
            return "Command specific information"
        elif self.value == 0x02:
            return "Sense key specific"
        elif self.value == 0x03:
            return "Field replaceable unit"
        elif self.value == 0x04:
            return "Stream commands"
        elif self.value == 0x05:
            return "Block commands"
        elif self.value == 0x06:
            return "OSD object identification"
        elif self.value == 0x07:
            return "OSD response integrity check value"
        elif self.value == 0x08:
            return "OSD attribute identification"
        elif self.value == 0x09:
            return "ATA Return"
        elif self.value in range(0x0A, 0x80):
            return "Reserved [{}]".format(hex(self.value))
        elif self.value in range(0x80, 0x100):
            return "Vendor Specific [{}]".format(hex(self.value))

    Information = 0x00
    CommandSpecificInformation = 0x01
    SenseKeySpecific = 0x02
    FieldReplaceableUnit = 0x03
    StreamCommands = 0x04
    BlockCommands = 0x05
    OSDObjectIdentification = 0x06
    OSDResponseIntegrityCheckValue = 0x07
    OSDAttributeIdentification = 0x08
    ATAReturn = 0x09


class SenseDescriptor(bytes):
    if hasattr(sg_lib.lib, 'sg_get_sense_descriptors_str'):
        def __repr__(self):
            return "<{}.{}: {} ({})>".format(self.__class__.__name__,
                                             self.__class__.__module__,
                                             str(self),
                                             " ".join("{:02x}".format(n) for n in self))

        def to_str(self, leadin=''):
            leadin_ = leadin.encode('utf-8')
            buf = sg_lib.ffi.new('char[2048]')
            sg_lib.lib.sg_get_sense_descriptors_str(leadin_, self, len(self), 2048, buf)
            return sg_lib.ffi.string(buf).decode('utf-8')
    else:
        def __repr__(self):
            return "<{}.{}: {}>".format(self.__class__.__name__,
                                        self.__class__.__module__,
                                        str(self))

        def to_str(self, leadin=''):
            return leadin + " ".join("{:02x}".format(n) for n in self)

    def __str__(self):
        return self.to_str()


class Sense(Buffer):
    """
    SCSI Sense buffer에 관련된 기능들을 구현한 클래스
    """

    def normalize(self) -> SenseHeader:
        header = sg_lib.ffi.new('struct sg_scsi_sense_hdr *')
        if sg_lib.lib.sg_scsi_normalize_sense(self.ptr, len(self.ptr), header) == 0:
            return None
        hdr = SenseHeader(*iter(getattr(header, k) for k in SenseHeader._fields))
        return hdr

    def descriptor(self, desc_type: Union[int, DescriptorTypes]) -> SenseDescriptor:
        desc = sg_lib.lib.sg_scsi_sense_desc_find(self.ptr, len(self.ptr), desc_type)
        if desc == sg_lib.ffi.NULL:
            return None
        desc_len = sg_lib.ffi.cast('uint8_t *', desc)[1] + 2
        return SenseDescriptor(sg_lib.ffi.buffer(desc, desc_len))

    @property
    def sense_key(self) -> Union[int, SenseKeyCodes]:
        sk = sg_lib.lib.sg_get_sense_key(self.ptr, len(self.ptr))
        try:
            return SenseKeyCodes(sk)
        except ValueError:
            return sk

    @property
    def asc_ascq_desc(self) -> str:
        h = self.normalize()
        buf = sg_lib.ffi.new('char[128]')
        sg_lib.lib.sg_get_asc_ascq_str(h.asc, h.ascq, 128, buf)
        return sg_lib.ffi.string(buf).decode('utf-8')

    @property
    def filemark_eom_ili(self) -> bool:
        return sg_lib.lib.sg_get_sense_filemark_eom_ili(
                self.ptr, len(self.ptr),
                sg_lib.ffi.NULL, sg_lib.ffi.NULL, sg_lib.ffi.NULL) != 0

    @property
    def filemark(self) -> bool:
        v = sg_lib.ffi.new('int *')
        sg_lib.lib.sg_get_sense_filemark_eom_ili(
                self.ptr, len(self.ptr),
                v, sg_lib.ffi.NULL, sg_lib.ffi.NULL)
        return v[0] != 0

    @property
    def eom(self) -> bool:
        v = sg_lib.ffi.new('int *')
        sg_lib.lib.sg_get_sense_filemark_eom_ili(
                self.ptr, len(self.ptr),
                sg_lib.ffi.NULL, v, sg_lib.ffi.NULL)
        return v[0] != 0

    @property
    def ili(self) -> bool:
        v = sg_lib.ffi.new('int *')
        sg_lib.lib.sg_get_sense_filemark_eom_ili(
                self.ptr, len(self.ptr),
                sg_lib.ffi.NULL, sg_lib.ffi.NULL, v)
        return v[0] != 0

    @property
    def progress(self) -> float:
        v = sg_lib.ffi.new('int *')
        if sg_lib.lib.sg_get_sense_progress_fld(self.ptr, len(self.ptr), v) == 0:
            return None
        return v[0] / 65536

    def to_str(self, leadin=''):
        buf = sg_lib.ffi.new('char[2048]')
        sg_lib.lib.sg_get_sense_str(leadin.encode('utf-8'), self.ptr, len(self.ptr),
                                    False, 2048, buf)
        return sg_lib.ffi.string(buf).decode('utf-8')

    def __str__(self):
        return self.to_str()

    @property
    def err_category(self):
        return sg_lib.lib.sg_get_category_sense_str(self.ptr, len(self.ptr))

