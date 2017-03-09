from . import _pysg, sg_lib
import enum
import re

aligned_new = _pysg.ffi.new_allocator(_pysg.lib.aligned_malloc, _pysg.lib.aligned_free, True)


# Internal uses
def enumize(mod, prefix):
    lib = mod.lib
    def decorator(e):
        def gen():
            for k in dir(lib):
                if k.startswith(prefix):
                    k_ = k[len(prefix):]
                    if "0" <= k_[0] <= "9":
                        yield prefix[0] + k_, getattr(lib, k)
                    else:
                        yield k_, getattr(lib, k)
        e_ = e(e.__name__, dict(gen()))
        e_.__doc__ = e.__doc__
        return e_
    return decorator


def enum_str(fn, maxlen, *args):
    tp = 'char[{}]'.format(maxlen)
    def __str__(self):
        buf = _pysg.ffi.new(tp)
        fn(self.value, maxlen, buf, *args)
        return _pysg.ffi.string(buf).decode('utf-8')

    return __str__


def to_enum_name(s):
    s = _pysg.ffi.string(s)
    return ''.join(x.capitalize() for x in re.split('[^a-zA-Z0-9]+', s.decode('utf-8')))


def desig_enum_generator(type_name, fn_name, def_name, start, end, **kwargs):
    if hasattr(sg_lib.lib, fn_name):
        fn = getattr(sg_lib.lib, fn_name)
        class Enum(int, HexValueEnum):
            def __str__(self):
                return fn(self)

        values = dict((to_enum_name(fn(v)), v)
                       for v in range(start, end + 1))
    else:
        values = dict(('{}{}'.format(def_name, hex(v)), v) for v in range(start, end + 1))
        Enum = enum.Enum
    values.update(kwargs)
    values['Any'] = -1
    return Enum(type_name, values)


class HexValueEnum(enum.Enum):
    """
    sgutils 내에 사용되는 Enum 중, 값에 대한 description을 지원하는 경우
    `repr()`을 적용했을 때 description을 보여주게끔 하는 Enum 확장
    """
    def __repr__(self):
        return "<{}.{}: {}({})>".format(self.__class__.__name__, self.name,
                                        hex(self.value), str(self))


class DescEnum(enum.Enum):
    """
    sgutils 내에 사용되는 Enum 중, 값에 대한 description을 지원하는 경우
    `repr()`을 적용했을 때 description을 보여주게끔 하는 Enum 확장
    실제 integer 값을 보여주지 않는다.
    """
    def __repr__(self):
        return "<{}.{}: {}>".format(self.__class__.__name__, self.name,
                                    str(self))


