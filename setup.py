#!/usr/bin/env python
# encoding: utf-8

from setuptools import setup
from distutils.core import Command
from os.path import dirname, join as pjoin
from jenkins_autojobs.version import version

here = dirname(__file__)

classifiers = (
    'Environment :: Console',
    'Topic :: Utilities',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 2.7',
    # 'Programming Language :: Python :: 3.0',
    # 'Programming Language :: Python :: 3.1',
    # 'Programming Language :: Python :: 3.2',
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
    'python-jenkins>=0.2',
    'lxml>=2.2.0',
    'PyYAML>=3.10'
)

scripts = (
    'jenkins-makejobs-git = jenkins_autojobs.git:main',
    'jenkins-makejobs-svn = jenkins_autojobs.svn:main',
    'jenkins-makejobs-hg  = jenkins_autojobs.hg:main',
)

kw = {
    'name'                 : 'jenkins-autojobs',
    'version'              : version(),

    'description'          : 'Scripts for automatically creating jenkins jobs from scm branches',
    'long_description'     : open(pjoin(here, 'README.rst')).read(),

    'author'               : 'Georgi Valkov',
    'author_email'         : 'georgi.t.valkov@gmail.com',

    'license'              : 'New BSD License',

    'keywords'             : 'jenkins git mercurial svn',
    'classifiers'          : classifiers,

    'url'                  : 'https://github.com/gvalkov/jenkins-autojobs',

    'packages'             : ('jenkins_autojobs',),
    'entry_points'         : {'console_scripts'  : scripts},
    'install_requires'     : requires,
    'cmdclass'             : {},

    'zip_safe'             : True,
}

class PyTest(Command):
    user_options = []
    def initialize_options(self): pass
    def finalize_options(self):   pass
    def run(self):
        from subprocess import call
        errno = call(('py.test', 'tests'))
        raise SystemExit(errno)

kw['cmdclass']['test'] = PyTest
setup(**kw)
