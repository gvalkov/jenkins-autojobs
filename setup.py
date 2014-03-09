#!/usr/bin/env python
# encoding: utf-8

from sys import exit
from os.path import dirname, join as pjoin
from setuptools import setup
from setuptools.command.test import test as TestCommand
from jenkins_autojobs import version

here = dirname(__file__)

classifiers = (
    'Environment :: Console',
    'Topic :: Utilities',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.3',
    'License :: OSI Approved :: BSD License',
    #'Development Status :: 1 - Planning',
    #'Development Status :: 2 - Pre-Alpha',
    'Development Status :: 3 - Alpha',
    # 'Development Status :: 4 - Beta',
    #'Development Status :: 5 - Production/Stable',
    #'Development Status :: 6 - Mature',
    #'Development Status :: 7 - Inactive',
)

requires = (
    'jenkins-webapi>=0.2.0',
    'lxml>=3.2.3',
    'PyYAML>=3.10'
)

scripts = (
    'jenkins-makejobs-git = jenkins_autojobs.git:main',
    'jenkins-makejobs-svn = jenkins_autojobs.svn:main',
    'jenkins-makejobs-hg  = jenkins_autojobs.hg:main',
)

kw = {
    'name'             : 'jenkins-autojobs',
    'version'          : version,
    'description'      : 'Scripts for automatically creating Jenkins jobs from scm branches',
    'long_description' : open(pjoin(here, 'README.rst')).read(),
    'author'           : 'Georgi Valkov',
    'author_email'     : 'georgi.t.valkov@gmail.com',
    'license'          : 'Revised BSD License',
    'keywords'         : 'jenkins git mercurial svn subversion',
    'classifiers'      : classifiers,
    'url'              : 'https://github.com/gvalkov/jenkins-autojobs',
    'packages'         : ('jenkins_autojobs',),
    'entry_points'     : {'console_scripts'  : scripts},
    'install_requires' : requires,
    'tests_require'    : ['pytest'],
    'cmdclass'         : {},
    'zip_safe'         : False,
}

class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True
    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        exit(errno)

kw['cmdclass']['test'] = PyTest

if __name__ == '__main__':
    setup(**kw)
