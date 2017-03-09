from .. import _pysg, sg_lib
from ..enum import PeripheralDeviceTypes, PDT
from typing import Optional, Type, NewType, Union, Tuple


class Command(object):
    """
    SCSI Command 관련 함수를 모아놓은 클래스
    """

    _command_map = []

    service_action = None
    control = None

    @staticmethod
    def command_property(msb: Union[Tuple[int, int], int],
                         lsb: Union[Tuple[int, int], int, type(None)]=None):
        """
        CDB 내의 필드를 지정할 때 사용한다.

        :param msb: 필드의 msb 위치를 지정한다.
        :type msb: Union[Tuple[int, int], int]
        :param lsb: 필드의 lsb 위치를 지정한다.
        :type lsb: Union[Tuple[int, int], int, type(None)]
        :return: 해당 필드를 사용 가능하게 하는 `property` 객체
        :rtype: property

        .. note::
            lsb와 msb를 지정하는데 몇 가지 조건이 있다.
                * lsb가 생략된 경우 msb와 동일한 값을 가진 것으로 취급한다.
                * msb나 lsb에 tuple이 지정된 경우, 첫 번째 원소를 byte
                  offset으로, 두 번째 원소를 bit offset으로 사용한다.
                * msb에 int가 지정된 경우 byte offset으로 사용하고 bit
                  offset은 7을 사용한다.
                * lsb에 int가 지정된 경우 byte offset으로 사용하고 bit
                  offset은 0을 사용한다.
        """
        cast = _pysg.ffi.cast
        from_buffer = _pysg.ffi.from_buffer

        if lsb is None:
            lsb = msb
        if isinstance(msb, int):
            msb = (msb, 7)
        if isinstance(lsb, int):
            lsb = (lsb, 0)

        # Single bit 인 경우 boolean property로 사용
        if msb == lsb:
            B, b = msb
            def fget(self) -> int:
                v = self._cdb[B]
                return v & (1 << b) != 0

            def fset(self, val: bool):
                if val:
                    self._cdb[B] |= 1 << b
                else:
                    self._cdb[B] &= ~(1 << b)

        else:
            m_byte, m_bit = msb
            l_byte, l_bit = lsb
            size = l_byte - m_byte + 1
            m_bit += (size - 1) * 8
            if size < 1:
                raise ValueError("MSB must be prior of LSB")
            elif size == 1:
                tp = 'uint8_t *'
                def htoc(x):
                    return x

                def ctoh(x):
                    return x
            elif size == 2:
                tp = 'uint16_t *'
                m_bit += 8
                htoc = _pysg.lib.htobe16
                ctoh = _pysg.lib.be16toh
            elif size <= 4:
                tp = 'uint32_t *'
                m_byte = l_byte - 3
                htoc = _pysg.lib.htobe32
                ctoh = _pysg.lib.be32toh
            elif size <= 8:
                tp = 'uint64_t *'
                m_byte = l_byte - 7
                htoc = _pysg.lib.htobe64
                ctoh = _pysg.lib.be64toh
            else:
                raise ValueError("More than 64bit integer is not supported")

            m_bit += 1

            def fget(self) -> int:
                val = cast(tp, self._cdb[m_byte:l_byte + 1])
                return (ctoh(val[0]) & ((1 << m_bit) - 1)) >> l_bit

            def fset(self, val: int):
                val_ = cast(tp, self._cdb[m_byte:l_byte + 1])
                val_ = ctoh(val_[0])
                mask = ~((1 << m_bit) - 1) | ((1 << l_bit) - 1)
                val_ = ctoh(val_[0]) & mask
                new_val = val_ | ((val << l_bit) & ((1 << m_bit) - 1))
                val_[0] = htoc(new_val)

        return property(fget, fset)

    @classmethod
    def register(cls, c: Optional[Type['Command']]=None, **kwargs):
        """
        `kwarg` 로 주어진 조건을 만족시키면 `cdb` 를 분석할 때 주어진 `c`
        command 로 간주할 수 있도록 힌트를 추가하는 함수

        :param c: `Command` 를 상속받은 클래스
        :type c: Optional[Type[Command]]
        :return: `c`
        :rtype: Optional[Type[Command]]
        """

        def decorator(c_):
            # 분석용 맵에 추가하고 추가되는 클래스는 독자적인 분석용 맵을
            # 갖도록 한다. 이를 통해 재귀적 분석을 가능하게 한다.
            cls._command_map.append((kwargs.items(), c_))
            c_._command_map = []
            return c_

        if c is None:
            return decorator
        else:
            return decorator(c)

    def __init__(self, seq: bytes, peri_type: PeripheralDeviceTypes=PDT.DISK):
        """
        주어진 CDB sequence 로 SCSI Command 객체를 생성한다.

        :param seq: CDB sequence
        :type seq: bytes
        :param peri_type: Peripheral Type
        :type peri_type: PeripheralDeviceTypes

        .. note::
            `peri_type` 은 description 을 볼 때만 참고하므로 중요하지 않다.
        """
        self._cdb = None
        self._cdb_buf = None
        self._cdb_len = None
        cdb0 = seq[0]
        if cdb0 >= 0xc0:
            l = len(seq)
        elif cdb0 == 0x7f:
            l = seq[7] + 8
        else:
            l = sg_lib.lib.sg_get_command_size(cdb0)
        self._cdb = _pysg.ffi.new('uint8_t[{}]'.format(l), seq)
        self._cdb_buf = _pysg.ffi.buffer(self._cdb)
        self._cdb_len = l
        self.peri_type = peri_type

    @property
    def cdb(self) -> bytes:
        """
        CDB 값

        :return: CDB
        :rtype: bytes
        
        .. note::
            `bytes` 로 반환되므로 `cffi`를 넘어갈 때 GC 되어버려 이상한 값을
            가리키게 될 가능성이 있고, `Command` 객체가 수정되어도 이미 `cdb`
            property로 얻어낸 값은 변하지 않는다.
        """
        return self._cdb_buf[:]

    @property
    def opcode(self) -> int:
        """
        Operation code

        :return: Operation code
        :rtype: int
        """
        return self._cdb[0]

    @property
    def name(self) -> str:
        """
        Command name given pointer to the cdb. Certain command names
        depend on peripheral type (give 0 or -1 if unknown).

        :return: Command name
        :rtype: str
        """
        buf = _pysg.ffi.new('char[128]')
        sg_lib.lib.sg_get_command_name(_pysg.ffi.cast('unsigned char *', self._cdb),
                                        self.peri_type, 128, buf)
        return _pysg.ffi.string(buf).decode('utf-8')

    def __str__(self):
        return "{} ({})".format(self.name, ' '.join('{:02x}'.format(cdb)
                                                    for cdb in self._cdb))

    def __repr__(self):
        return "<{}.{}: {}>".format(self.__class__.__module__,
                                    self.__class__.__qualname__, str(self))

    def __len__(self):
        return self._cdb_len

DerivedCommand = NewType('DerivedCommand', Command)


def command(seq: bytes, peri_type: PeripheralDeviceTypes=PDT.DISK)\
        -> DerivedCommand:
    """
    `Command.register()` 로 등록된 클래스들을 찾으면서 맞는 클래스로
    만들어준다.

    :param seq: CDB sequence
    :type seq: bytes
    :param peri_type: Peripheral Device Type
    :type peri_type: PeripheralDeviceTypes
    :return: Instance of Command-derived class
    :rtype: DerivedCommand
    """

    cmd = Command(seq, peri_type)
    ok = True
    while cmd._command_map and ok:
        ok = True
        for cond, c in cmd._command_map:
            ok = True
            for k, v in cond:
                if not hasattr(v, '__contains__'):
                    v = (v,)
                if getattr(cmd, k) not in v:
                    ok = False
                    break
            if ok:
                cmd = c(seq=seq, peri_type=peri_type)
                break
    return cmd

