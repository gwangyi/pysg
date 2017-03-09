from setuptools import setup

setup(
    name="pysg",
    description="cffi-based sg3utils wrapper for python",
    license="MIT",
    version="0.1",
    author='Sungkwang Lee',
    maintainer='Sungkwang Lee',
    author_email='gwangyi.kr@gmail.com',
    url='https://github.com/gwangyi/pysg',
    packages=["pysg"],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3',],
    setup_requires=['cffi>=1.0.0', 'pycparserlibc'],
    cffi_modules=[
        'pysg/build.py:sg_lib_builder',
        'pysg/build.py:sg_pt_builder',
        'pysg/build.py:sg_cmds_builder',
        'pysg/build.py:_pysg_builder'],
    install_requires=['cffi>=1.0.0'],
    dependency_links=[
        'git+https://github.com/gwangyi/pycparserlibc#egg=pycparserlibc',
    ],
)
