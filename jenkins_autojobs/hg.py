#!/usr/bin/env python
# encoding: utf-8

'''
Automatically create jenkins jobs for the branches in a mercurial repository.
Documentation: https://github.com/gvalkov/jenkins-autojobs/
'''

import os
import re
import sys
import ast

from jenkins_autojobs.main import main as _main, debug_refconfig
from jenkins_autojobs.util import sanitize, check_output, merge
from jenkins_autojobs.job import Job


# We do this to decouple the current interpreter version from the
# mercurial interpreter version. The mercurial helper script is called
# with the python version specified in the config file.
hg_remote_helper_path = os.path.join(
    os.path.split(__file__)[0],
    'hg_remote_helper.py'
)

def hg_branch_iter_remote(repo, python):
    cmd = [python, hg_remote_helper_path, '-r', repo]
    out = check_output(cmd)
    out = ast.literal_eval(out.decode('utf8'))
    return [i[0] for i in out]

def hg_branch_iter_local(repo, python=None):
    cmd = ['hg', '-y', 'branches', '-c', '-R', repo]
    out = check_output(cmd).decode('utf8').split(os.linesep)

    out = (re.split('\s+', i, 1) for i in out if i)
    return (name for name, rev in out)

def list_branches(config):
    # Should 'hg branches' or peer.branchmap be used.
    islocal = os.path.isdir(config['repo'])
    branch_iter = hg_branch_iter_local if islocal else hg_branch_iter_remote
    python = config.get('python', 'python')

    return branch_iter(config['repo'], python)

def create_job(ref, template, config, ref_config):
    '''Create a jenkins job.
       :param ref: hg branch name
       :param template: the config of the template job to use
       :param config: global config (parsed yaml)
       :param ref_config: the effective config for this branch
    '''

    print('\nprocessing branch: %s' % ref)

    sanitized_ref = sanitize(ref, ref_config['sanitize'])
    sanitized_ref = sanitized_ref.replace('/', ref_config['namesep'])

    match = ref_config['re'].match(ref)
    groups, groupdict = match.groups(), match.groupdict()

    # Placeholders available to the 'substitute' and 'namefmt' options.
    fmtdict = {
        'repo':   sanitize(config['repo'], ref_config['sanitize']),
        'branch': sanitized_ref,
        'repo-orig': config['repo'],
        'branch-orig': ref,
    }

    job_name = ref_config['namefmt'].format(*groups, **merge(groupdict, fmtdict))
    job = Job(job_name, ref, template, _main.jenkins)

    fmtdict['job_name'] = job_name

    print('. job name: %s' % job.name)
    print('. job exists: %s' % job.exists)

    try:
        scm_el = job.xml.xpath('scm[@class="hudson.plugins.mercurial.MercurialSCM"]')[0]
    except IndexError:
        msg = 'Template job %s is not configured to use Mercurial as an SCM'
        raise RuntimeError(msg % template)  # :bug:

    # Set branch.
    el = scm_el.xpath('//branch')

    # Newer version of the jenkins hg plugin store the branch in the
    # 'revision' element.
    if not el:
        el = scm_el.xpath('//revision')
    el[0].text = ref

    # Set the state of the newly created job.
    job.set_state(ref_config['enable'])

    # Since some plugins (such as sidebar links) can't interpolate the
    # job name, we do it for them.
    job.substitute(list(ref_config['substitute'].items()), fmtdict, groups, groupdict)

    job.create(
        ref_config['overwrite'],
        ref_config['build-on-create'],
        config['dryrun']
    )

    if config['debug']:
        debug_refconfig(ref_config)
    return job_name

def main(argv=sys.argv, config=None):
    _main(argv[1:], config=config, create_job=create_job, list_branches=list_branches)

if __name__ == '__main__':
    main()
