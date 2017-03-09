from ._common import enumize, enum_str, desig_enum_generator
from ._common import HexValueEnum, DescEnum
from . import sg_lib, sg_pt
import enum

try:
    IntFlag = enum.IntFlag
except AttributeError:
    IntFlag = enum.IntEnum


@enumize(sg_lib, 'PDT_')
class PeripheralDeviceTypes(int, HexValueEnum):
    """
    SCSI Peripheral Device Types (PDT) [5 bit field]
    """

    # `str()` 을 호출하면 `sg_lib.lib.sg_get_pdt_str()` 함수로 설명을 가져오며,
    # 그 최대 길이는 48 byte이다.
    __str__ = enum_str(sg_lib.lib.sg_get_pdt_str, 48)

    # sg_lib_pdt_decay 함수가 구현되어 있지 않은 경우가 있다
    if hasattr(sg_lib.lib, 'sg_lib_pdt_decay'):
        def decay(self) -> 'PeripheralDeviceTypes':
            """
            Some lesser used PDTs share a lot in common with a more used PDT.
            Examples are PDT_ADC decaying to PDT_TAPE and PDT_ZBC to PDT_DISK.
            If such a lesser used ``pdt`` is given to this function, then it will
            return the more used PDT (i.e. "decays to"); otherwise `pdt` is
            returned.
            Valid for ``pdt`` 0 to 31, for other values returns 0.

            :returns: Decayed PDT
            :rtype: PeripheralDeviceTypes
            """
            return self.__class__(sg_lib.lib.sg_lib_pdt_decay(self.value))
    else:
        def decay(self) -> 'PeripheralDeviceTypes':
            """
            `sg_lib.lib.sg_lib_pdt_decay()` 가 지원되지 않음.

            :returns: self
            :rtype: PeripheralDeviceTypes
            """
            return self

PDT = PeripheralDeviceTypes


@enumize(sg_lib, 'SAM_STAT_')
class StatusCodes(int, HexValueEnum):
    """
    The SCSI status codes as found in SAM-4 at www.T10.org
    """

    # `str()` 을 호출하면 `sg_get_scsi_status_str()` 함수로 설명을 가져오며,
    # 그 최대 길이는 128 byte이다.
    __str__ = enum_str(sg_lib.lib.sg_get_scsi_status_str, 128)

SAM_STAT = StatusCodes


@enumize(sg_lib, 'SPC_SK_')
class SenseKeyCodes(int, HexValueEnum):
    """
    The SCSI sense key codes as found in SPC-4 at www.t10.org
    """

    # `str()` 을 호출하면 `sg_get_sense_key_str()` 함수로 설명을 가져오며,
    # 그 최대 길이는 80 byte이다.
    __str__ = enum_str(sg_lib.lib.sg_get_sense_key_str, 80)

SPC_SK = SenseKeyCodes


@enumize(sg_lib, 'TPROTO_')
class TransportProtocols(int, HexValueEnum):
    """
    Transport protocol identifiers of just Protocol identifiers
    """

    __str__ = enum_str(sg_lib.lib.sg_get_trans_proto_str, 128)

TPROTO = TransportProtocols


@enumize(sg_lib, 'SG_LIB_CAT_')
class ErrorCategories(int, DescEnum):
    """
    The `sg_err_category_sense()` function returns one of the following.
    These may be used as exit status values (from a process). Notice that
    some of the lower values correspond to SCSI sense key values.
    """

    __str__ = enum_str(sg_lib.lib.sg_get_category_sense_str, 80, False)

SG_LIB_CAT = ErrorCategories

DesignatorTypes = desig_enum_generator(
        'DesignatorTypes', 'sg_get_desig_type_str', 'Type', 1, 15, VendorSpecific=0)

DesignatorCodeSets = desig_enum_generator(
        'DesignatorCodeSets', 'sg_get_desig_code_set_str', 'CodeSet', 0, 15)

DesignatorAssociations = desig_enum_generator(
        'DesignatorAssociations', 'sg_get_desig_assoc_str', 'Assoc', 0, 3)

DesigType = DesignatorTypes
DesigCodeSet = DesignatorCodeSets
DesigAssoc = DesignatorAssociations

 
@enumize(sg_pt, 'SCSI_PT_FLAGS_')
class PTFlags(IntFlag):
    pass


@enumize(sg_pt, 'SCSI_PT_DO_')
class DoPTResult(enum.IntEnum):
    pass


@enumize(sg_pt, 'SCSI_PT_RESULT_')
class PTResult(enum.IntEnum):
    pass


