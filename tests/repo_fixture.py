# -*- coding: utf-8; -*-

import os
import shutil

from os.path import join as pjoin, abspath, dirname
from tempfile import mkdtemp, mkstemp
from contextlib import contextmanager
from subprocess import check_call
from itertools import product


here = abspath(dirname(__file__))

def repo_fixture(repo_type):
    types = {
        'git': GitRepo,
        'hg':  HgRepo,
        'svn': SvnRepo,
        'svn-nested': SvnNestedRepo,
    }
    repo = types[repo_type]()
    print('Creating temporary %s repo: %s' % (repo_type, repo.dir))
    repo.init()
    return repo


class TmpRepo(object):
    def __init__(self, d=pjoin(here, 'tmp/repos')):
        if not os.path.exists(d): os.makedirs(d)
        self.dir = mkdtemp(dir=d)
        self.url = 'file://%s' % abspath(self.dir)

    def clean(self):
        shutil.rmtree(self.dir)

    def chdir(self):
        os.chdir(self.dir)

    @contextmanager
    def branch(self, name, **kw):
        if GitRepo == self.__class__ and 'base' not in kw:
            kw['base'] = 'master'

        self.mkbranch(name, **kw)
        yield name
        self.rmbranch(name)

    @contextmanager
    def branches(self, *args, **kw):
        if GitRepo == self.__class__ and 'base' not in kw:
            kw['base'] = 'master'

        [self.mkbranch(name, **kw) for name in args]
        yield
        [self.rmbranch(name) for name in args]


class GitRepo(TmpRepo):
    def __init__(self, d=pjoin(here, 'tmp/repos')):
        super(GitRepo, self).__init__()
        self.gitcmd = ['git', '--git-dir=%s/.git' % self.dir]

    def init(self):
        cmd = ('git', 'init', self.dir)
        check_call(cmd)

        cmd = self.gitcmd + ['commit', '--allow-empty', '-m', '++']
        check_call(cmd)

    def mkbranch(self, name, base='master'):
        cmd = self.gitcmd + ['branch', name, base]
        check_call(cmd)

    def rmbranch(self, name):
        cmd = self.gitcmd + ['branch', '-D', name]
        check_call(cmd)


class SvnRepo(TmpRepo):
    def __init__(self, d=pjoin(here, 'tmp/repos')):
        super(SvnRepo, self).__init__()

    def init(self):
        cmd = ('svnadmin', 'create', self.dir)
        check_call(cmd)

        cmd = 'svn mkdir {url}/trunk {url}/branches {url}/experimental -m ++'.format(url=self.url)
        check_call(cmd, shell=True)

    def mkbranch(self, name):
        cmd = ('svn', 'cp', '--parents', '%s/trunk/' % self.url,
               '%s/%s' % (self.url, name),
               '-m', '++')
        check_call(cmd)

    def rmbranch(self, name):
        cmd = ('svn', 'rm', '%s/%s' % (self.url, name), '-m', '++')
        check_call(cmd)


class SvnNestedRepo(TmpRepo):
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


class HgRepo(TmpRepo):
    def __init__(self, d=pjoin(here, 'tmp/repos')):
        super(HgRepo, self).__init__()

    def init(self):
        cmd = 'hg', 'init', self.dir
        check_call(cmd)

        mkstemp(dir=self.dir)

        cmd = 'hg', 'commit', '-A', '-m', "++"
        check_call(cmd, cwd=self.dir)

    def mkbranch(self, name):
        cmd = 'hg', 'branch', name
        check_call(cmd, cwd=self.dir)

        mkstemp(dir=self.dir)

        cmd = 'hg', 'commit', '-A', '-m', '++'
        check_call(cmd, cwd=self.dir)

    def rmbranch(self, name):
        shutil.rmtree(self.dir)
        self.init()
