# -*- coding: utf-8; -*-

import re
import yaml

from os.path import basename, abspath
from sys import exit, argv
from copy import deepcopy
from getopt import getopt
from getpass import getpass
from functools import partial
from subprocess import CalledProcessError

from lxml import etree
from jenkins import Jenkins, JenkinsError
from requests.exceptions import RequestException

from jenkins_autojobs import version
from jenkins_autojobs.util import *


try:
    from itertools import ifilterfalse as filterfalse
except ImportError:
    from itertools import filterfalse

try:
    from collections import OrderedDict
except ImportError:
    from python26_support import OrderedDict


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
  -P scm password (read from stdin)

Jenkins Options:
  -j <arg> jenkins url
  -u <arg> jenkins username
  -p <arg> jenkins password
  -U jenkins username (read from stdin)
  -P jenkins password (read from stdin)\
''' % basename(argv[0])


# the global connection to jenkins
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
    opts, args = parse_args(argv, getoptfmt)

    if not args and not config:
        print(usage) ; exit(1)

    # load config, set default values and compile regexes
    if not config :
        yamlfn = args[-1]
        print('loading config from "%s"' % abspath(yamlfn))
        config = yaml.load(open(yamlfn))

    config = c = get_default_config(config, opts)

    if config['debughttp']:
        enable_http_logging()

    # connect to jenkins
    try:
        global jenkins
        jenkins = main.jenkins = Jenkins(c['jenkins'], c['username'], c['password'])
    except (RequestException, JenkinsError) as e:
        print(e); exit(1)

    # get all the template names that the config refenrences
    templates = set(i['template'] for i in c['refs'].values())

    # check if all referenced template jobs exist on the server
    missing = list(filterfalse(jenkins.job_exists, templates))
    if missing:
        missing.insert(0, '\nconfig references non-existant template jobs:')
        print('\n - '.join(missing)); exit(1)

    # convert them to etree objects of the templates' config xmls
    templates = dict((i, get_job_etree(i)) for i in templates)

    # list all git refs, svn branches etc (implemented by child classes)
    try:
        branches = list(list_branches(config))
    except CalledProcessError as e:
        print('! cannot list branches')
        print('! command %s failed' % ' '.join(e.cmd))
        exit(1)

    # see if some of the branches are ignored
    ignored, branches = get_ignored(branches, c['ignore'])

    if ignored:
        msg = ['\nexplicitly ignored:'] + ignored
        print('\n - '.join(msg))

    # get branch config for each branch
    configs = map(partial(resolveconfig, config), branches)
    configs = zip(branches, configs)
    configs = filter(lambda x: bool(x[1]), configs)

    # the names of all successfully created or updated jobs
    job_names = [config['template']]
    for branch, branch_config in configs:
        name = create_job(branch, templates[branch_config['template']], config, branch_config)
        job_names.append(name)

    if config['cleanup']:
        cleanup(config, job_names, jenkins)


def cleanup(config, job_names, jenkins, verbose=True):
    print('\ncleaning up old jobs:')

    tag = '</createdByJenkinsAutojobs>'
    tagxpath = 'createdByJenkinsAutojobs/tag/text()'

    managed_jobs = (job for job in jenkins.jobs if tag in job.config)
    removed_jobs = []

    for job in managed_jobs:
        if job.name not in job_names and job.exists:
            # if cleanup is a tag name, only cleanup builds with that tag
            if isinstance(config['cleanup'], str):
                xml = etree.fromstring(job.config.encode('utf8'))
                clean_tag = xml.xpath(tagxpath)
                if not config['cleanup'] in clean_tag:
                    continue

            removed_jobs.append(job)
            if not config['dryrun']:
                job.delete()
            print(' - %s' % job.name)

    if not removed_jobs:
        print('. nothing to do')


def parse_args(argv, fmt):
    '''Parse getopt arguments as a dictionary.'''
    opts, args = getopt(argv, fmt)
    opts = dict(opts)

    if '-v' in opts:
        print('jenkins-autojobs version %s' % version)
        exit(0)

    return opts, args


def get_default_config(config, opts):
    '''Set default config values and compile regexes.'''

    c, o = deepcopy(config), opts

    # default global settings (not inheritable)
    c['dryrun'] = False
    c['debug']  = False
    c['debughttp'] = False
    c['cleanup']  = config.get('cleanup', False)
    c['username'] = config.get('username', None)
    c['password'] = config.get('password', None)

    # default settings for each git ref/branch/ config
    c['defaults'] = {
        'namesep':    c.get('namesep', '-'),
        'namefmt':    c.get('namefmt', '{shortref}'),
        'overwrite':  c.get('overwrite', True),
        'enable':     c.get('enable', 'sticky'),
        'substitute': c.get('substitute', {}),
        'template':   c.get('template'),
        'sanitize':   c.get('sanitize', {'@!?#&|\^_$%*': '_'}),
        'tag':        c.get('tag', []),
    }

    # some options can be overwritten on the command line
    if '-r' in o: c['repo'] = o['-r']
    if '-j' in o: c['jenkins'] = o['-j']
    if '-n' in o: c['dryrun'] = True
    if '-d' in o: c['debug'] = True
    if '-t' in o: c['debughttp'] = True

    # jenkins authentication options
    if '-u' in o: c['username'] = o['-u']
    if '-p' in o: c['password'] = o['-p']

    c['scm-username'] = c.get('scm-username', None) #:todo
    c['scm-password'] = c.get('scm-password', None) #:todo

    if '-U' in o: c['username'] = raw_input('User: ')
    if '-P' in o: c['password'] = getpass()

    # compile ignore regexes
    c.setdefault('ignore', {})
    c['ignore'] = [re.compile(i) for i in c['ignore']]

    if not 'refs' in c:
        c['refs'] = ['.*']

    # get the effective (accounting for inheritance) config for all refs
    cfg = get_effective_branch_config(c['refs'], c['defaults'])
    c['refs'] = cfg

    return c


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

    return ec


def get_ignored(branches, regexes):
    '''Get refs, excluding ignored.'''

    isignored = partial(anymatch, regexes)
    ignored, branches = filtersplit(isignored, branches)

    return ignored, branches


def resolveconfig(effective_config, branch):
    '''Resolve a ref to its effective config.'''

    for regex, config in effective_config['refs'].items():
        if regex.match(branch):
            config['re'] = regex
            return config.copy()


def get_job_etree(job):
    res = jenkins.job(job).config
    res = etree.fromstring(res.encode('utf8'))
    return res


def debug_refconfig(ref_config):
    print('. config:')
    for k,v in ref_config.items():
        if k == 're':
            print('  . %s: %s' % (k, v.pattern))
            continue
        if v: print('  . %s: %s' % (k, v))


def enable_http_logging():
    import logging, httplib
    httplib.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger('requests.packages.urllib3')
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True
