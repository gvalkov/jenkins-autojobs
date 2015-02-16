# -*- coding: utf-8; -*-

from jenkins_autojobs import svn
from itertools import product
from repo_fixture import TmpRepo

from subprocess import check_call
from jenkins_autojobs.svn import svn_wildcard_ls, list_branches


#-----------------------------------------------------------------------------
class SvnRepo(TmpRepo):
    def init(self):
        cmd = ('svnadmin', 'create', self.dir)
        check_call(cmd)

        dirs = product(
            [self.url],
            ['', 'sub1', 'sub2'],
            'ABCD',
            ['trunk', 'tags', 'branches/1', 'branches/2', 'branches/3'],
        )
        urls = map('/'.join, dirs)

        cmd = ['svn', 'mkdir', '-m', '++', '--parents']
        cmd += urls

        check_call(cmd)

def test_dirs():
    repo = SvnRepo()
    repo.init()
    config = {
        'repo': repo.url,
        'branches': [],
        'scm-username': None,
        'scm-password': None,
    }

    config['branches'] = [repo.url + '/A/branches']
    assert list_branches(config) == [
        'A/branches/1', 'A/branches/2', 'A/branches/3'
    ]

    config['branches'] = [repo.url + '/*/branches']
    assert list_branches(config) == [
        'A/branches/1', 'A/branches/2', 'A/branches/3',
        'B/branches/1', 'B/branches/2', 'B/branches/3',
        'C/branches/1', 'C/branches/2', 'C/branches/3',
        'D/branches/1', 'D/branches/2', 'D/branches/3',
    ]

    config['branches'] = [repo.url + '/*/*/branches/']
    assert list_branches(config) == [
        'sub1/A/branches/1', 'sub1/A/branches/2', 'sub1/A/branches/3',
        'sub1/B/branches/1', 'sub1/B/branches/2', 'sub1/B/branches/3',
        'sub1/C/branches/1', 'sub1/C/branches/2', 'sub1/C/branches/3',
        'sub1/D/branches/1', 'sub1/D/branches/2', 'sub1/D/branches/3',
        'sub2/A/branches/1', 'sub2/A/branches/2', 'sub2/A/branches/3',
        'sub2/B/branches/1', 'sub2/B/branches/2', 'sub2/B/branches/3',
        'sub2/C/branches/1', 'sub2/C/branches/2', 'sub2/C/branches/3',
        'sub2/D/branches/1', 'sub2/D/branches/2', 'sub2/D/branches/3'
    ]
