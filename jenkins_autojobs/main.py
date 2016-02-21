# -*- coding: utf-8; -*-

from __future__ import print_function
from __future__ import absolute_import

import os
import re
import sys
import copy
import argparse
import subprocess

from getpass import getpass
from functools import partial

import lxml.etree
import ruamel.yaml as yaml

from jenkins import Jenkins, JenkinsError
from requests.exceptions import RequestException, HTTPError

from . import __version__
from . import utils, job


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
Usage: %s [options] <config.yaml>

General Options:
  -n, --dry-run             simulate execution
  -v, --version             show version and exit
  -d, --debug               debug config inheritance
  -t, --debug-http          debug http requests

Repository Options:
  -r, --repo-url <arg>      repository url
  -y, --scm-user <arg>      scm username (use '-' to read from stdin)
  -o, --scm-pass <arg>      scm password (use '-' to read from stdin)

Jenkins Options:
  -j, --jenkins-url <arg>   jenkins server url
  -u, --jenkins-user <arg>  jenkins username (use '-' to read from stdin)
  -p, --jenkins-pass <arg>  jenkins password (use '-' to read from stdin)
  --no-verify-ssl           do not verify jenkins server certificate
  --cert-bundle <path>      path to CA bundle file or directory
  --client-cert <path>      path to SSL client certificate

A client certificate can be specified as a single file, containing the
private key and certificate) or as 'path/to/client.cert:path/to/client.key'.\
''' % os.path.basename(sys.argv[0])


#-----------------------------------------------------------------------------
# The *global* connection to jenkins - assigned in main().
jenkins = None


def parseopts(args):
    parser = argparse.ArgumentParser()
    opt = parser.add_argument
    opt('-n', '--dry-run',    action='store_true')
    opt('-v', '--version',    action='version', version='%(prog) version ' + __version__)
    opt('-d', '--debug',      action='store_true')
    opt('-t', '--debug-http', action='store_true')
    opt('--no-verify-ssl',    action='store_false', dest='verify_ssl')
    opt('--cert-bundle')
    opt('--client-cert')

    opt('-r', '--repo-url')
    opt('-y', '--scm-user', type=utils.PromptArgtype(input,   'SCM User: '))
    opt('-o', '--scm-pass', type=utils.PromptArgtype(getpass, 'SCM Password: '))

    opt('-j', '--jenkins-url')
    opt('-u', '--jenkins-user', type=utils.PromptArgtype(input,   'Jenkins User: '))
    opt('-p', '--jenkins-pass', type=utils.PromptArgtype(getpass, 'Jenkins Password: '))
    opt('yamlconfig', metavar='config.yaml', type=argparse.FileType('r'), nargs="?")

    return parser.parse_args(args)


def main(argv, create_job, list_branches, config=None):
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
        sys.exit(0)

    opts = parseopts(argv)

    if not opts.yamlconfig and not config:
        print(usage, file=sys.stderr)
        print('error: config file not specified', file=sys.stderr)
        sys.exit(2)

    # Load config, set default values and compile regexes.
    if not config:
        print('loading config from "%s"' % os.path.abspath(opts.yamlconfig.name))
        config = yaml.load(opts.yamlconfig)

    config = c = get_default_config(config, opts)

    if config['debughttp']:
        enable_http_logging()

    # Connect to jenkins.
    try:
        global jenkins
        verify = c['cert-bundle'] if c['cert-bundle'] else c['verify-ssl']
        jenkins = main.jenkins = Jenkins(c['jenkins'], c['username'], c['password'],
                                         verify=verify, cert=c['client-cert'])
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

    filter_function = partial(
        filter_jobs,
        by_views=config['cleanup-filters']['views'],
        by_name_regex=config['cleanup-filters']['jobs']
    )

    removed_jobs = []
    managed_jobs = get_managed_jobs(created_job_names, jenkins, filter_function)

    for job, job_config in managed_jobs:
        # If cleanup is a tag name, only cleanup builds with that tag.
        if isinstance(config['cleanup'], str):
            clean_tags = get_autojobs_tags(job_config, config['tag-method'])
            if not config['cleanup'] in clean_tags:
                if config['debug']:
                    print('. skipping %s' % job.name)
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

def get_autojobs_tags(job_config, method):
    xml = lxml.etree.fromstring(job_config.encode('utf8'))
    if method == 'element':
        tags = xml.xpath('createdByJenkinsAutojobs/tag/text()')

    elif method == 'description':
        _, description = job.Job.find_description_el(xml)
        description = description[0].text if description else ''
        tags = re.findall(r'\n\(jenkins-autojobs-tag: (.*)\)', description)

    tags = tags[0].split() if tags else []
    return tags

def filter_jobs(jenkins, by_views=(), by_name_regex=()):
    '''Select only jobs that belong to a given view or the names of which match a regex.'''
    jobs = set()

    if not by_views and not by_name_regex:
        return jenkins.jobs

    # Select jobs in the by_views list.
    for view_name in by_views:
        view_jobs = jenkins.view_jobs(view_name)
        jobs.update(view_jobs)  # set.update() is a union operation.

    # Select jobs names that match the by_name_regex list.
    for job in jenkins.jobs:
        if utils.anymatch(by_name_regex, job.name):
            jobs.add(job)

    return jobs

def get_managed_jobs(created_job_names, jenkins, filter_function=None, safe_codes=(403,)):
    '''
    Returns jobs which were created by jenkins-autojobs. This is determined by
    looking for a special string or element in the job's config.xml.
    '''

    tag_el = '</createdByJenkinsAutojobs>'
    tag_desc = '(created by jenkins-autojobs)'

    if callable(filter_function):
        jobs = filter_function(jenkins)
    else:
        jobs = jenkins.jobs

    for job in jobs:
        if job.name in created_job_names:
            continue
        try:
            job_config = job.config
            if (tag_desc in job_config) or (tag_el in job_config):
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
    c['verify-ssl']   = config.get('verify-ssl', True)
    c['cert-bundle']  = config.get('cert-bundle', None)
    c['client-cert']  = config.get('client-cert', None)
    c['tag-method']   = config.get('tag-method', 'description')
    c['cleanup-filters'] = config.get('cleanup-filters', {})

    # Default settings for each git ref/branch config.
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

    # Default cleanup filters.
    c['cleanup-filters']['views'] = c['cleanup-filters'].get('views', [])
    c['cleanup-filters']['jobs']  = c['cleanup-filters'].get('jobs', [])

    # Make sure some options are always lists.
    c['defaults']['view'] = utils.pluralize(c['defaults']['view'])

    # Options that can be overwritten from the command-line.
    if o.repo_url:     c['repo'] = opts.repo_url
    if o.jenkins_url:  c['jenkins'] = opts.jenkins_url
    if o.dry_run:      c['dryrun'] = True
    if o.debug:        c['debug'] = True
    if o.debug_http:   c['debughttp'] = True
    if o.cert_bundle:  c['cert-bundle'] = opts.cert_bundle
    if o.client_cert:  c['client-cert'] = opts.client_cert
    if not o.verify_ssl:  c['verify-ssl'] = opts.verify_ssl

    # Jenkins authentication options.
    if o.jenkins_user: c['username'] = o.jenkins_user
    if o.jenkins_pass: c['password'] = o.jenkins_pass

    # SCM authentication options.
    if o.scm_user: c['scm-username'] = o.scm_user
    if o.scm_pass: c['scm-password'] = o.scm_pass

    # Compile ignore regexes.
    c.setdefault('ignore', {})
    c['ignore'] = [re.compile(i) for i in c['ignore']]

    # Compile cleanup-filters job name regexes.
    c['cleanup-filters']['jobs'] = [re.compile(i) for i in c['cleanup-filters']['jobs']]

    # The 'All' view doesn't have an API endpoint (i.e. no /view/All/api).
    # Since all jobs are added to it by default, we can ignore all other views.
    if 'All' in c['cleanup-filters']['views']:
        c['cleanup-filters']['views'] = []

    if 'refs' not in c:
        c['refs'] = ['.*']

    if c['client-cert'] and ':' in c['client-cert']:
        c['client-cert'] = tuple(c['client-cert'].split(':', 1))

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
