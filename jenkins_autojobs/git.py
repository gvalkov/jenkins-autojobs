#!/usr/bin/env python
# encoding: utf-8

'''
Automatically create jenkins jobs for the refs in a git repository.
Documentation: http://gvalkov.github.com/jenkins-autojobs/
'''

import re

from os import linesep, path
from sys import exit, argv
from subprocess import Popen, PIPE

from lxml import etree
from jenkins_autojobs.main import main as _main, debug_refconfig
from jenkins_autojobs.job import Job


def git_refs_iter_local(repo):
    cmd = ('git', 'show-ref')
    out = Popen(cmd, stdout=PIPE, cwd=repo).communicate()[0]
    out = out.split(linesep)

    return (ref for sha, ref in [i.split() for i in out if i])

def git_refs_iter_remote(repo):
    cmd = ('git', 'ls-remote', repo)
    out = Popen(cmd, stdout=PIPE).communicate()[0]
    out = out.split(linesep)

    for sha, ref in (i.split() for i in out if i):
        if not ref.startswith('refs/'):
            continue
        # :todo: generalize
        if ref.endswith('^{}'):
            continue

        yield ref

def list_branches(config):
    # should ls-remote or git show-ref be used
    islocal = path.isdir(config['repo'])
    refs_iter = git_refs_iter_local if islocal else git_refs_iter_remote

    return refs_iter(config['repo'])


def create_job(ref, template, config, ref_config):
    '''Create a jenkins job.
       :param ref: git ref name (ex: refs/heads/something)
       :param template: the config of the template job to use
       :param config: global config (parsed yaml)
       :param ref_config: the effective config for this ref
    '''

    print('\nprocessing ref: {}'.format(ref))

    # job names with '/' in them are problematic
    sanitized_ref = ref.replace('/', ref_config['namesep'])
    shortref = re.sub('^refs/(heads|tags|remotes)/', '', ref)
    groups = ref_config['re'].match(ref).groups()

    # placeholders available to the 'substitute' and 'namefmt' options
    fmtdict = {
        'ref'      : sanitized_ref,
        'shortref' : shortref.replace('/', ref_config['namesep']),
        'ref-orig' : ref,
        'shortref-orig' : shortref,
    }

    job_name = ref_config['namefmt'].format(*groups, **fmtdict)
    job = Job(job_name, template, _main.jenkins)

    fmtdict['job_name'] = job_name

    print('. job name: {}'.format(job.name))
    print('. job exists: {}'.format(job.exists))

    try:
        scm_el = job.xml.xpath('scm[@class="hudson.plugins.git.GitSCM"]')[0]
    except IndexError:
        msg = 'Template job {} is not configured to use Git as an SCM'
        raise RuntimeError(msg.format(template))  #:bug:

    # get remote name
    remote = scm_el.xpath('//hudson.plugins.git.UserRemoteConfig/name')
    remote = remote[0].text if remote else 'origin'

    # set branch
    el = scm_el.xpath('//hudson.plugins.git.BranchSpec/name')[0]
    # :todo: jenkins is being very caprecious about the branchspec
    # el.text = '{}/{}'.format(remote, shortref)  # :todo:
    el.text = shortref

    # set the branch that git plugin will locally checkout to
    el = scm_el.xpath('//localBranch')
    el = etree.SubElement(scm_el, 'localBranch') if not el else el[0]

    el.text = shortref # the original shortref (with '/')

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
