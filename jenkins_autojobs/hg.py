#!/usr/bin/env python
# encoding: utf-8

'''
Automatically create jenkins jobs for the branches in a mercurial repository.
Documentation: http://gvalkov.github.com/jenkins-autojobs/
'''

import re

from os import linesep, path
from sys import exit, argv
from tempfile import NamedTemporaryFile
from subprocess import Popen, PIPE

from lxml import etree
from jenkins_autojobs.main import main as _main, debug_refconfig
from jenkins_autojobs.job import Job


# decouple the current interpreter version from the mercurial
# interpreter version
hg_list_remote_py = '''
from mercurial import ui, hg, node

peer = hg.peer(ui.ui(), {}, '%s')
for name, rev in peer.branchmap().items():
    print name, node.short(rev[0])
'''


def hg_branch_iter_remote(repo):
    with NamedTemporaryFile() as fh:
        fh.write(hg_list_remote_py % repo)
        fh.flush()
        out = Popen(('python', fh.name), stdout=PIPE).communicate()[0]

    out = out.split(linesep)
    return (name for name, rev in (i.split() for i in out if i))

def hg_branch_iter_local(repo):
    cmd = ('hg', '-y', 'branches', '-c', '-R', repo)
    out = Popen(cmd, stdout=PIPE).communicate()[0]
    out = out.split(linesep)

    out = (re.split('\s+', i, 1) for i in out if i)
    return (name for name, rev in out)

def list_branches(config):
    # should 'hg branches' or peer.branchmap be used
    islocal = path.isdir(config['repo'])
    branch_iter = hg_branch_iter_local if islocal else hg_branch_iter_remote

    return branch_iter(config['repo'])


def create_job(ref, template, config, ref_config):
    '''Create a jenkins job.
       :param ref: hg branch name
       :param template: the config of the template job to use
       :param config: global config (parsed yaml)
       :param ref_config: the effective config for this branch
    '''

    print('\nprocessing branch: {}'.format(ref))

    # job names with '/' in them are problematic
    sanitized_ref = ref.replace('/', ref_config['namesep'])
    shortref = sanitized_ref
    groups = ref_config['re'].match(ref).groups()

    # placeholders available to the 'substitute' and 'namefmt' options
    fmtdict = {
        'branch' : sanitized_ref,
        'branch-orig' : ref,
    }

    job_name = ref_config['namefmt'].format(*groups, **fmtdict)
    job = Job(job_name, template, _main.jenkins)

    fmtdict['job_name'] = job_name

    print('. job name: {}'.format(job.name))
    print('. job exists: {}'.format(job.exists))

    try:
        scm_el = job.xml.xpath('scm[@class="hudson.plugins.mercurial.MercurialSCM"]')[0]
    except IndexError:
        msg = 'Template job {} is not configured to use Mercurial as an SCM'
        raise RuntimeError(msg.format(template))  #:bug:

    # set branch
    el = scm_el.xpath('//branch')[0]
    el.text = ref

    # set the state of the newly created job
    job.set_state(ref_config['enable'])

    # since some plugins (such as sidebar links) can't interpolate the job
    # name, we do it for them
    job.substitute(list(ref_config['substitute'].items()), fmtdict)

    job.create(ref_config['overwrite'], config['dryrun'])

    if config['debug']:
        debug_refconfig(ref_config)


def main(argv=argv, config=None):
    _main(argv[1:], config=config, create_job=create_job, list_branches=list_branches)

if __name__ == '__main__':
    main()
