#!/usr/bin/env python
# encoding: utf-8

from sys import version_info
from setuptools import setup
from jenkins_autojobs import __version__


classifiers = [
    'Environment :: Console',
    'Topic :: Utilities',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'License :: OSI Approved :: BSD License',
    'Development Status :: 5 - Production/Stable',
    #'Development Status :: 6 - Mature',
    #'Development Status :: 7 - Inactive',
]

requires = [
    'jenkins-webapi>=0.5.0',
    'lxml>=3.2.3',
    'PyYAML>=3.11',
]

if version_info <= (2, 7):
    requires.append('ordereddict>=1.1')

scripts = [
    'jenkins-makejobs-git = jenkins_autojobs.git:_main',
    'jenkins-makejobs-svn = jenkins_autojobs.svn:_main',
    'jenkins-makejobs-hg  = jenkins_autojobs.hg:_main',
]

kw = {
    'name':             'jenkins-autojobs',
    'version':          __version__,
    'description':      'Scripts for automatically creating Jenkins jobs from SCM branches',
    'long_description': open('README.rst').read(),
    'author':           'Georgi Valkov',
    'author_email':     'georgi.t.valkov@gmail.com',
    'license':          'Revised BSD License',
    'keywords':         'jenkins git mercurial svn subversion',
    'classifiers':      classifiers,
    'url':              'https://github.com/gvalkov/jenkins-autojobs',
    'packages':         ['jenkins_autojobs'],
    'entry_points':     {'console_scripts': scripts},
    'install_requires': requires,
    'tests_require':    ['pytest'],
    'zip_safe':         False,
}

if __name__ == '__main__':
    setup(**kw)
