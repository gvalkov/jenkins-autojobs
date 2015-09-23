# -*- coding: utf-8; -*-

import pytest

from os import chdir
from os.path import abspath, dirname, join


#-----------------------------------------------------------------------------
here = abspath(dirname(__file__))

def pytest_addoption(parser):
    parser.addoption('--runslow', action='store_true', help='run slow tests')

def pytest_runtest_setup(item):
    chdir(join(here, 'etc'))
    if 'slow' in item.keywords and not item.config.getoption('--runslow'):
        pytest.skip('need --runslow option to run')
