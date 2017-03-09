import sys
import os
import functools
from cffi import FFI
import pycparserlibc
from pycparserlibc.cpp import Preprocessor

cpp_args = ["-I/usr/local/include", "-I/usr/include"]

preprocess = functools.partial(pycparserlibc.preprocess,
                               cpp_args=cpp_args,
                               fake_defs=True)


def prepare(mod):
    pp = Preprocessor()
    include_stmt = ''.join(('#include <scsi/', mod, '.h>'))
    header = preprocess(include_stmt, preprocessor=pp)
    builder = FFI()
    builder.set_source('pysg.' + mod,
                       include_stmt,
                       libraries=["sgutils2"])
    builder.cdef(header)
    for m, v in pp.macros.items():
        if v.value and v.value[0].type in ('CPP_INTEGER', 'CPP_ID'):
            builder.cdef("const int {};".format(m))

    return builder

sg_lib_builder = prepare('sg_lib')
sg_pt_builder = prepare('sg_pt')
sg_cmds_builder = prepare('sg_cmds')

_pysg_builder = FFI()
_pysg_builder.set_source('pysg._pysg', r"""
#include <unistd.h>
#include <stdlib.h>
#include <endian.h>
#include <stdio.h>

void * aligned_malloc(int size) {
    void * ptr = 0;
    if(posix_memalign(&ptr, sysconf(_SC_PAGESIZE), size) < 0) {
        return 0;
    }
    return ptr;
}

void aligned_free(void * ptr) {
    free(ptr);
}
""")

_pysg_builder.cdef(r"""
uint16_t htobe16(uint16_t);
uint16_t htole16(uint16_t);
uint16_t be16toh(uint16_t);
uint16_t le16toh(uint16_t);
uint32_t htobe32(uint32_t);
uint32_t htole32(uint32_t);
uint32_t be32toh(uint32_t);
uint32_t le32toh(uint32_t);
uint64_t htobe64(uint64_t);
uint64_t htole64(uint64_t);
uint64_t be64toh(uint64_t);
uint64_t le64toh(uint64_t);
FILE * fdopen(int, const char *);
void fclose(FILE *);
void setbuf(FILE *, char *);
void * aligned_malloc(int);
void aligned_free(void *);
""")

if __name__ == "__main__":
    for builder in (sg_lib_builder, sg_pt_builder, sg_cmds_builder, _pysg_builder):
        builder.compile(verbose=True)

