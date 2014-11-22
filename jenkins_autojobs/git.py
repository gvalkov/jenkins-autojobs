#!/usr/bin/env python
# encoding: utf-8

'''
Automatically create jenkins jobs for the refs in a git repository.
Documentation: http://gvalkov.github.com/jenkins-autojobs/
'''

import re

from os import linesep, path
from sys import exit, argv

from lxml import etree
from jenkins_autojobs.main import main as _main, debug_refconfig
from jenkins_autojobs.util import sanitize, check_output, merge
from jenkins_autojobs.job import Job


#-----------------------------------------------------------------------------
def git_refs_iter_local(repo):
    cmd = ('git', 'show-ref')
    out = check_output(cmd, cwd=repo).split(linesep)

    return (ref for sha, ref in [i.split() for i in out if i])

def git_refs_iter_remote(repo):
    cmd = ('git', 'ls-remote', repo)
    out = check_output(cmd).decode('utf8').split(linesep)

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

       :param ref:         git ref name (ex: refs/heads/something)
       :param template:    the config of the template job to use
       :param config:      global config (parsed yaml)
       :param ref_config:  the effective config for this ref
       :returns:           the name of the newly created job
    '''

    print('\nprocessing ref: %s' % ref)
    shortref = re.sub('^refs/(heads|tags|remotes)/', '', ref)

    sanitized_ref = sanitize(ref, ref_config['sanitize'])
    sanitized_shortref = sanitize(shortref, ref_config['sanitize'])

    # Job names with '/' in them are problematic (todo: consolidate with sanitize()).
    sanitized_ref = sanitized_ref.replace('/', ref_config['namesep'])
    sanitized_shortref = sanitized_shortref.replace('/', ref_config['namesep'])

    match = ref_config['re'].match(ref)
    groups, groupdict = match.groups(), match.groupdict()

    # Placeholders available to the 'substitute' and 'namefmt' options.
    fmtdict = {
        'ref':      sanitized_ref,
        'shortref': sanitized_shortref,
        'ref-orig': ref,
        'shortref-orig': shortref,
    }

    job_name = ref_config['namefmt'].format(*groups, **merge(groupdict, fmtdict))
    job = Job(job_name, ref, template, _main.jenkins)

    fmtdict['job_name'] = job_name

    print('. job name: %s' % job.name)
    print('. job exists: %s' % job.exists)

    try:
        scm_el = job.xml.xpath('scm[@class="hudson.plugins.git.GitSCM"]')[0]
    except IndexError:
        msg = 'Template job %s is not configured to use Git as an SCM'
        raise RuntimeError(msg % template)  # :bug:

    # Get remote name.
    remote = scm_el.xpath('//hudson.plugins.git.UserRemoteConfig/name')
    remote = remote[0].text if remote else 'origin'

    # Set branch.
    el = scm_el.xpath('//hudson.plugins.git.BranchSpec/name')[0]
    # :todo: jenkins is being very capricious about the branch-spec
    # el.text = '%s/%s' % (remote, shortref)  # :todo:
    el.text = shortref

    # Set the branch that the git plugin will locally checkout to.
    el = scm_el.xpath('//localBranch')
    el = etree.SubElement(scm_el, 'localBranch') if not el else el[0]

    el.text = shortref  # the original shortref (with '/')

    # Set the state of the newly created job.
    job.set_state(ref_config['enable'])

    # Since some plugins (such as sidebar links) can't interpolate the
    # job name, we do it for them.
    job.substitute(list(ref_config['substitute'].items()), fmtdict, groups, groupdict)

    job.create(ref_config['overwrite'], config['dryrun'], tag=ref_config['tag'])

    if config['debug']:
        debug_refconfig(ref_config)

    return job_name

def main(argv=argv, config=None):
    _main(argv[1:], config=config, create_job=create_job, list_branches=list_branches)

if __name__ == '__main__':
    main()
