# -*- coding: utf-8; -*-

from os import chdir
from os.path import abspath, dirname, join


#-----------------------------------------------------------------------------
here = abspath(dirname(__file__))

def pytest_runtest_setup(item):
    chdir(join(here, 'etc'))
