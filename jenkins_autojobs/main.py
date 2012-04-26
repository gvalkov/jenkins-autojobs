
import re
import yaml

from os.path import basename, abspath
from sys import exit, argv
from copy import deepcopy
from getopt import getopt
from getpass import getpass
from functools import partial
from collections import OrderedDict

from jenkins import Jenkins, JenkinsException
from lxml import etree

from jenkins_autojobs.version import version_verbose
from jenkins_autojobs.util import *

try:
    from urllib2 import URLError
except ImportError:
    from urllib.error import URLError

try:
    from itertools import ifilterfalse as filterfalse
except ImportError:
    from itertools import filterfalse


usage = '''\
Usage: %s [-rvdjnyoupUYOP] <config.yaml>

General Options:
  -n dry run
  -v show version and exit
  -d debug config inheritance

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


def main(argv, create_job, list_branches,  getoptfmt='vdnr:j:u:p:y:o:UPYO', config=None):
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
        print('loading config from "{}"'.format(abspath(yamlfn)))
        config = yaml.load(open(yamlfn))

    config = c = get_default_config(config, opts)

    # connect to jenkins
    try:
        global jenkins
        jenkins = main.jenkins = Jenkins(c['jenkins'], c['username'], c['password'])
    except (URLError, JenkinsException) as e:
        print(e); exit(1)

    # get all the template names that the config refenrences
    templates = set(i['template'] for i in c['refs'].values())

    # check if all referenced template jobs exist on the server
    missing = list(filterfalse(jenkins.job_exists, templates))
    if missing:
        missing.insert(0, '\nconfig references non-existant template jobs:')
        print('\n - '.join(missing)); exit(1)

    # convert them to etree objects of the templates' config xmls
    templates = {i: get_job_etree(i) for i in templates}

    # list all git refs, svn branches etc (implemented by child classes)
    branches = list_branches(config)

    # see if some of the branches are ignored
    ignored, branches = get_ignored(branches, c['ignore'])

    if ignored:
        msg = ['\nexplicitly ignored:'] + ignored
        print('\n - '.join(msg))

    # get branch config for each branch
    configs = map(partial(resolveconfig, config), branches)
    configs = zip(branches, configs)
    configs = filter(lambda x: bool(x[1]), configs)

    for branch, branch_config in configs:
        create_job(branch, templates[branch_config['template']], config, branch_config)


def parse_args(argv, fmt):
    '''Parse getopt arguments as a dictionary.'''
    opts, args = getopt(argv, fmt)
    opts = dict(opts)

    if opts.has_key('-v'):
        print(version_verbose()) ; exit(0)

    return opts, args


def get_default_config(config, opts):
    '''Set default config values and compile regexes.'''

    c, o = deepcopy(config), opts

    # default global settings (not inheritable)
    c['dryrun'] = False
    c['debug'] = False

    # default settings for each git ref/branch/ config
    c['defaults'] = {
        'namesep':    c.get('namesep', '-'),
        'namefmt':    c.get('namefmt', '{shortref}'),
        'overwrite':  c.get('overwrite', True),
        'enable':     c.get('enable', 'sticky'),
        'substitute': c.get('substitute', {}),
        'template':   c.get('template'),
    }

    # some options can be overwritten on the command line
    if '-r' in o: c['repo'] = o['-r']
    if '-j' in o: c['jenkins'] = o['-j']
    if '-n' in o: c['dryrun'] = True
    if '-d' in o: c['debug'] = True

    # jenkins authentication options
    c['username'] = o.get('-u', None)
    c['password'] = o.get('-p', None)

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
            key, overrides = entry.items()[0]
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
    res = jenkins.get_job_config(job)
    res = etree.fromstring(res)
    return res


def debug_refconfig(ref_config):
    print('. config:')
    for k,v in ref_config.items():
        if k == 're':
            print('  . {}: {}'.format(k, v.pattern))
            continue
        if v: print('  . {}: {}'.format(k, v))
