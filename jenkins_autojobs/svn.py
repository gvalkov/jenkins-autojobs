#!/usr/bin/env python
# encoding: utf-8

'''
Automatically create jenkins jobs for the branches in a svn repository.
Documentation: https://github.com/gvalkov/jenkins-autojobs/
'''

from __future__ import absolute_import

import os
import sys
import subprocess

from . import job, main, utils


def svn_ls(url, username=None, password=None, dirsonly=True):
    cmd = ['svn', 'ls', '--trust-server-cert', '--non-interactive']

    # :todo: plaintext (will probably have to use the bindings).
    if username:
        cmd += ['--username', username]
    if password:
        cmd += ['--password', password]

    cmd.append(url)
    out = utils.check_output(cmd).decode('utf8').split(os.linesep)

    if dirsonly:
        out = [i.rstrip('/') for i in out if i.endswith('/')]

    return out

def svn_wildcard_ls(url, repo, username=None, password=None, dirsonly=True):
    left, wcard, right = url.partition('*')
    right = right.lstrip('/')
    branches = []

    if not wcard:
        try:
            return svn_ls(left, username, password, True)
        except subprocess.CalledProcessError:
            return []
    else:
        for dirname in svn_ls(left, username, password, True):
            url = os.path.join(left, dirname, right)
            res = svn_wildcard_ls(url, repo, username, password, True)
            rel = url.replace(repo, '')
            branches.extend(os.path.join(rel, i) for i in res)
        return branches

def list_branches(config):
    c = config
    branches = []

    for url in c['branches']:
        if '*' in url:
            res = svn_wildcard_ls(url, c['repo'], c['scm-username'], c['scm-password'])
            res = [i.lstrip('/') for i in res]
        else:
            res = svn_ls(url, c['scm-username'], c['scm-password'])
            rel = url.replace(c['repo'], '').lstrip('/')
            res = [os.path.join(rel, i) for i in res]
        branches.extend(res)
    return branches

def create_job(branch, template, config, branch_config):
    '''Create a jenkins job.
       :param branch: svn branch name (ex: branches/feature-one)
       :param template: the config of the template job to use
       :param config: global config (parsed yaml)
       :param branch_config: the effective config for this branch
    '''

    print('\nprocessing branch: %s' % branch)

    # Job names with '/' in them are problematic.
    sanitized_branch = branch.replace('/', branch_config['namesep'])

    match = branch_config['re'].match(branch)
    groups, groupdict = match.groups(), match.groupdict()

    # Placeholders available to the 'substitute' and 'namefmt' options.
    fmtdict = {
        'branch': branch.split('/')[-1],
        'path': branch.replace('/', branch_config['namesep']),
        'repo': utils.sanitize(config['repo'], branch_config['sanitize']),
        'path-orig': branch,
        'repo-orig': config['repo'],
    }

    job_name = branch_config['namefmt'].format(*groups, **utils.merge(groupdict, fmtdict))
    job_obj = job.Job(job_name, branch, template, main.jenkins)

    fmtdict['job_name'] = job_name

    print('. job name: %s' % job_obj.name)
    print('. job exists: %s' % job_obj.exists)

    try:
        scm_el = job_obj.xml.xpath('scm[@class="hudson.scm.SubversionSCM"]')[0]
    except IndexError:
        msg = 'Template job %s is not configured to use SVN as an SCM'
        raise RuntimeError(msg % template)  # :bug:

    # set branch
    el = scm_el.xpath('//remote')[0]
    el.text = os.path.join(config['repo'], branch)

    # Set the branch that git plugin will locally checkout to.
    el = scm_el.xpath('//local')[0]
    el.text = '.'

    # Set the state of the newly created job.
    job_obj.set_state(branch_config['enable'])

    # Since some plugins (such as sidebar links) can't interpolate the
    # job name, we do it for them.
    job_obj.substitute(list(branch_config['substitute'].items()), fmtdict, groups, groupdict)

    job_obj.create(
        branch_config['overwrite'],
        branch_config['build-on-create'],
        config['dryrun'],
        tag=branch_config['tag']
    )

    if config['debug']:
        main.debug_refconfig(branch_config)
    return job_name

def _main(argv=sys.argv, config=None):
    main.main(argv[1:], config=config, create_job=create_job, list_branches=list_branches)

if __name__ == '__main__':
    _main()
