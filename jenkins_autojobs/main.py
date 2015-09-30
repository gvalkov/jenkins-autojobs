# -*- coding: utf-8; -*-

from __future__ import absolute_import

import os
import re
import sys
import copy
import yaml
import getopt
import getpass
import subprocess

from functools import partial

import lxml.etree
from jenkins import Jenkins, JenkinsError
from requests.exceptions import RequestException, HTTPError

from . import __version__
from . import utils


#-----------------------------------------------------------------------------
# Compatibility imports.
try:
    from itertools import ifilterfalse as filterfalse
except ImportError:
    from itertools import filterfalse

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

try:
    input = raw_input
except NameError:
    pass


#-----------------------------------------------------------------------------
usage = '''\
Usage: %s [-rvdtjnyoupUYOP] <config.yaml>

General Options:
  -n dry run
  -v show version and exit
  -d debug config inheritance
  -t debug http requests

Repository Options:
  -r <arg> repository url
  -y <arg> scm username
  -o <arg> scm password
  -Y scm username (read from stdin)
  -O scm password (read from stdin)

Jenkins Options:
  -j <arg> jenkins url
  -u <arg> jenkins username
  -p <arg> jenkins password
  -U jenkins username (read from stdin)
  -P jenkins password (read from stdin)\
''' % os.path.basename(sys.argv[0])


#-----------------------------------------------------------------------------
# The *global* connection to jenkins - assigned in main().
jenkins = None


def main(argv, create_job, list_branches, getoptfmt='vdtnr:j:u:p:y:o:UPYO', config=None):
    '''
    :param argv: command-line arguments to parse (defaults to sys.argv[1:])
    :param create_job: scm specific function that configures and creates jobs
    :param list_branches: scm specific function that lists all branches/refs
    :param getoptfmt: getopt short and long options
    :param config: a config dictionary to use instead of parsing the
                   configuration from yaml (useful for testing)
    '''

    if '-h' in argv or '--help' in argv:
        print(usage)
        exit(1)

    opts, args = parse_args(argv, getoptfmt)
    if not args and not config:
        print(usage)
        exit(1)

    # Load config, set default values and compile regexes.
    if not config:
        yamlfn = args[-1]
        print('loading config from "%s"' % abspath(yamlfn))
        config = yaml.load(open(yamlfn))

    config = c = get_default_config(config, opts)

    if config['debughttp']:
        enable_http_logging()

    # Connect to jenkins.
    try:
        global jenkins
        jenkins = main.jenkins = Jenkins(c['jenkins'], c['username'], c['password'])
    except (RequestException, JenkinsError) as e:
        print(e)
        sys.exit(1)

    #-------------------------------------------------------------------------
    # Get all the template names that the config references.
    templates = set(i['template'] for i in c['refs'].values())

    # Check if all referenced template jobs exist on the server.
    missing = list(filterfalse(jenkins.job_exists, templates))
    if missing:
        missing.insert(0, '\nconfig references non-existent template jobs:')
        print('\n - '.join(missing))
        sys.exit(1)

    # Convert them to etree objects of the templates' config xmls.
    templates = dict((i, get_job_etree(i)) for i in templates)

    #-------------------------------------------------------------------------
    # Check if all referenced views exist.
    view_names = set(view for i in c['refs'].values() for view in i['view'])
    missing = list(filterfalse(jenkins.view_exists, view_names))
    if missing:
        missing.insert(0, '\nconfig references non-existent views:')
        print('\n - '.join(missing))
        sys.exit(1)

    #-------------------------------------------------------------------------
    # List all git refs, svn branches etc (implemented by child classes).
    try:
        branches = list(list_branches(config))
    except subprocess.CalledProcessError as e:
        print('! cannot list branches')
        print('! command %s failed' % ' '.join(e.cmd))
        exit(1)

    # See if any of the branches are ignored.
    ignored, branches = get_ignored(branches, c['ignore'])

    if ignored:
        msg = ['\nexplicitly ignored:'] + ignored
        print('\n - '.join(msg))

    # Get branch config for each branch.
    configs = map(partial(resolveconfig, config), branches)
    configs = zip(branches, configs)
    configs = filter(lambda x: bool(x[1]), configs)

    # The names of all successfully created or updated jobs.
    job_names = {}
    for branch, branch_config in configs:
        tmpl = templates[branch_config['template']]
        job_name = create_job(branch, tmpl, config, branch_config)
        job_names[job_name] = branch_config

        # Add newly create jobs to views, if any.
        views = branch_config['view']
        for view_name in views:
            view = jenkins.view(view_name)
            if job_name in view:
                print('. job already in view: %s' % view_name)
            else:
                if not config['dryrun']:
                    jenkins.view_add_job(view_name, job_name)
                print('. job added to view: %s' % view_name)

    if config['cleanup']:
        job_names[config['template']] = {}
        cleanup(config, job_names, jenkins)

#-----------------------------------------------------------------------------
def cleanup(config, created_job_names, jenkins, verbose=True):
    print('\ncleaning up old jobs:')

    tagxpath = 'createdByJenkinsAutojobs/tag/text()'
    removed_jobs = []

    for job, job_config in get_managed_jobs(created_job_names, jenkins):
        # If cleanup is a tag name, only cleanup builds with that tag.
        if isinstance(config['cleanup'], str):
            xml = lxml.etree.fromstring(job_config.encode('utf8'))
            clean_tag = xml.xpath(tagxpath)
            if not config['cleanup'] in clean_tag:
                continue

        removed_jobs.append(job)
        if not config['dryrun']:
            job_removed = safe_job_delete(job)
        else:
            job_removed = True

        if job_removed:
            print(' - %s' % job.name)
        else:
            print(' ! permission denied for %s' % job.name)

    if not removed_jobs:
        print('. nothing to do')

def get_managed_jobs(created_job_names, jenkins, safe_codes=(403,)):
    tag = '</createdByJenkinsAutojobs>'

    for job in jenkins.jobs:
        if job.name in created_job_names:
            continue
        try:
            job_config = job.config
            if tag in job_config:
                yield job, job_config
        except HTTPError as error:
            if error.response.status_code not in safe_codes:
                raise

def safe_job_delete(job, safe_codes=(403,)):
    try:
        job.delete()
        return True
    except HTTPError as error:
        if error.response.status_code not in safe_codes:
            raise
        return False

#-----------------------------------------------------------------------------
def parse_args(argv, fmt):
    '''Parse getopt arguments as a dictionary.'''
    opts, args = getopt.getopt(argv, fmt)
    opts = dict(opts)

    if '-v' in opts:
        print('jenkins-autojobs version %s' % __version__)
        exit(0)

    return opts, args

#-----------------------------------------------------------------------------
def get_default_config(config, opts):
    '''Set default config values and compile regexes.'''

    c, o = copy.deepcopy(config), opts

    # Default global settings (not inheritable).
    c['dryrun'] = False
    c['debug']  = config.get('debug', False)
    c['debughttp'] = config.get('debughttp', False)
    c['cleanup']   = config.get('cleanup', False)
    c['username']  = config.get('username', None)
    c['password']  = config.get('password', None)
    c['scm-username'] = config.get('scm-username', None)
    c['scm-password'] = config.get('scm-password', None)

    # Default settings for each git ref/branch/ config.
    c['defaults'] = {
        'namesep':         c.get('namesep', '-'),
        'namefmt':         c.get('namefmt', '{shortref}'),
        'overwrite':       c.get('overwrite', True),
        'enable':          c.get('enable', 'sticky'),
        'substitute':      c.get('substitute', {}),
        'template':        c.get('template'),
        'sanitize':        c.get('sanitize', {'@!?#&|\^_$%*': '_'}),
        'tag':             c.get('tag', []),
        'view':            c.get('view', []),
        'build-on-create': c.get('build-on-create', False)
    }

    # Make sure some options are always lists.
    c['defaults']['view'] = utils.pluralize(c['defaults']['view'])

    # Some options can be overwritten on the command line.
    if '-r' in o: c['repo'] = o['-r']
    if '-j' in o: c['jenkins'] = o['-j']
    if '-n' in o: c['dryrun'] = True
    if '-d' in o: c['debug'] = True
    if '-t' in o: c['debughttp'] = True

    # Jenkins authentication options.
    if '-u' in o: c['username'] = o['-u']
    if '-p' in o: c['password'] = o['-p']
    if '-U' in o: c['username'] = input('Jenkins User: ')
    if '-P' in o: c['password'] = getpass.getpass('Jenkins Password: ')

    # SCM authentication options.
    if '-y' in o: c['scm-username'] = o['-y']
    if '-o' in o: c['scm-password'] = o['-o']
    if '-Y' in o: c['scm-username'] = input('SCM User: ')
    if '-O' in o: c['scm-password'] = getpass.getpass('SCM Password: ')

    # Compile ignore regexes.
    c.setdefault('ignore', {})
    c['ignore'] = [re.compile(i) for i in c['ignore']]

    if 'refs' not in c:
        c['refs'] = ['.*']

    # Get the effective (accounting for inheritance) config for all refs.
    cfg = get_effective_branch_config(c['refs'], c['defaults'])
    c['refs'] = cfg

    return c

#-----------------------------------------------------------------------------
def get_effective_branch_config(branches, defaults):
    '''Compile ref/branch regexes and map to their configuration with
       inheritance factored in (think maven help:effective-pom).'''

    ec = OrderedDict()
    assert isinstance(branches, (list, tuple))

    for entry in branches:
        if isinstance(entry, dict):
            key, overrides = list(entry.items())[0]
            config = defaults.copy()
            config.update(overrides)
            ec[re.compile(key)] = config
        else:
            ec[re.compile(entry)] = defaults

    # The 'All' view doesn't have an API endpoint (i.e. no /view/All/api).
    # Since all jobs are added to it by default, it is safe to ignore it.
    for config in ec.values():
        if 'All' in config['view']:
            config['view'].remove('All')

    return ec

def get_ignored(branches, regexes):
    '''Get refs, excluding ignored.'''

    isignored = partial(utils.anymatch, regexes)
    ignored, branches = utils.filtersplit(isignored, branches)

    return ignored, branches

def resolveconfig(effective_config, branch):
    '''Resolve a ref to its effective config.'''

    for regex, config in effective_config['refs'].items():
        if regex.match(branch):
            config['re'] = regex
            return config.copy()

def get_job_etree(job):
    res = jenkins.job(job).config
    res = lxml.etree.fromstring(res.encode('utf8'))
    return res

def debug_refconfig(ref_config):
    print('. config:')
    for k, v in ref_config.items():
        if k == 're':
            print('  . %s: %s' % (k, v.pattern))
            continue
        if v:
            print('  . %s: %s' % (k, v))

def enable_http_logging():
    import logging

    try:
        from http.client import HTTPConnection
    except ImportError:
        from httplib import HTTPConnection

    HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger('requests.packages.urllib3')
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True
