# -*- coding: utf-8; -*-

import io, os, pytest
import ruamel.yaml as yaml

from pytest import mark
from pytest import fixture, yield_fixture
from textwrap import dedent
from functools import partial

from repo_fixture import repo_fixture
from jenkins_autojobs import svn
from jenkins import Jenkins

#-----------------------------------------------------------------------------
# Fixtures and shortcuts.
cmd = partial(svn._main, ['jenkins-makejobs-svn'])

@yield_fixture(scope='module')
def repo():
    r = repo_fixture('svn')
    yield r
    r.clean()

@yield_fixture(scope='module')
def repo_nested():
    r = repo_fixture('svn-nested')
    yield r
    r.clean()

@fixture(scope='module')
def jenkins():
    print('Looking for a running Jenkins instance')
    webapi = Jenkins('http://127.0.0.1:60888')

    print('Removing all jobs ...')
    for job in webapi.jobs:
        webapi.job_delete(job.name)

    print('Creating test jobs ...')
    configxml = 'master-job-svn-config.xml'
    configxml = open(configxml).read().encode('utf8')
    webapi.job_create('master-job-svn', configxml)
    return webapi

@fixture(scope='function')
def config(jenkins, repo):
    base = u'''
    jenkins: {url}
    repo: {repo}

    branches:
      - {repo}/
      - {repo}/branches/
      - {repo}/experimental/

    template: master-job-svn

    namesep: '-'
    namefmt: 'changeme'
    overwrite: true
    enable: true

    substitute:
      '@@JOB_NAME@@' : 'changeme'

    ignore:
      - 'branches/.*-nobuild'
      - 'experimental/bob/.*'

    refs:
      - 'branches/(.*)'
      - 'experimental/(.*)':
          'template': 'master-job-svn'
          'namefmt':  'release-name'
          'enable':   false
    '''

    base = dedent(base).format(url=jenkins.url, repo=repo.url)
    base = yaml.load(io.StringIO(base))
    return base

@fixture(scope='function', autouse=True)
def cleanup(request, jenkins):
    def finalize():
        jobs = (job for job in jenkins.jobs if job.name != 'master-job-svn')
        for job in jobs:
            jenkins.job_delete(job.name)

    request.addfinalizer(finalize)


#------------------------------------------------------------------------------
params = [
    ['branches/feature-one', '{branch}', '-', 'feature-one'],
    ['branches/feature-one', '{path}',   '-', 'branches-feature-one'],
    ['branches/feature-one', '{path}',   '.', 'branches.feature-one'],
]
@pytest.mark.parametrize(['branch', 'namefmt', 'namesep', 'expected'], params)
def test_namefmt_namesep_global(jenkins, repo, config, branch, namefmt, namesep, expected):
    config['namefmt'] = namefmt
    config['namesep'] = namesep
    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(expected)


#------------------------------------------------------------------------------
params = [
    ['branches/feature-two', '{branch}',    '.', 'feature-two'],
    ['branches/feature-two', 'test.{path}', 'X', 'test.branchesXfeature-two'],
    ['branches/feature-two', 'test.{path}', '_', 'test.branches_feature-two'],
]
@pytest.mark.parametrize(['branch', 'namefmt', 'namesep', 'expected'], params)
def test_namefmt_namesep_inherit(jenkins, repo, config, branch, namefmt, namesep, expected):
    config['refs'] = [ {branch : {
        'namesep' : namesep,
        'namefmt' : namefmt, }}]

    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(expected)


#------------------------------------------------------------------------------
params = [
    ['experimental/john/bug/01', 'experimental/(.*)/bug/(.*)', '{0}-{1}', 'john-01'],
    ['tag/alpha/gamma',          '(.*)/(.*)/(.*)', 'test-{2}.{1}.{0}', 'test-gamma.alpha.tag'],
]
@pytest.mark.parametrize(['branch', 'regex', 'namefmt', 'expected'], params)
def test_namefmt_groups_inherit(jenkins, repo, config, branch, regex, namefmt, expected):
    config['branches'].append(os.path.join(config['repo'], os.path.dirname(branch)))
    config['namefmt'] = '.'
    config['refs'] = [{ regex : {'namefmt' : namefmt, }}]

    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(expected)


#------------------------------------------------------------------------------
params = [
    ['experimental/john',  ['experimental/.*']],
    ['experimental/v0.1-nobuild', ['.*-nobuild']]
]
@pytest.mark.parametrize(['branch', 'ignores'], params)
def test_ignore(jenkins, repo, config, branch, ignores):
    cleanup_jobs = branch.replace('/', config['namesep'])
    config['ignore'] = ignores
    with repo.branch(branch):
        cmd(config)
        assert not jenkins.job_exists(cleanup_jobs[0])


#------------------------------------------------------------------------------
params = [
    ['branches/alpha', '{repo}/branches/alpha',  '.']
]
@pytest.mark.parametrize(['branch', 'name', 'local'], params)
def test_configxml_global(jenkins, repo, config, branch, name, local):
    job = branch.split('/')[-1]
    name = name.format(**config)
    config['namefmt'] = '{branch}'

    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(job)

        configxml = jenkins.job_config_etree(job)

        scm_el = configxml.xpath('scm[@class="hudson.scm.SubversionSCM"]')[0]
        el = scm_el.xpath('//remote')[0]
        assert el.text == name

        assert scm_el.xpath('//local')[0].text == local


#------------------------------------------------------------------------------
def test_cleanup(jenkins, repo, config):
    config['cleanup'] = True
    config['namefmt'] = '{branch}'

    with repo.branches('branches/one', 'branches/two'):
        cmd(config)
        assert jenkins.job_exists('one')
        assert jenkins.job_exists('two')
        assert 'createdByJenkinsAutojobs' in jenkins.job('one').config

    with repo.branch('branches/one'):
        cmd(config)
        assert not jenkins.job_exists('two')


#------------------------------------------------------------------------------
def test_make_trunk(jenkins, repo, config):
    config['refs'] = [ {'trunk': {'namefmt': 'trunktest'}} ]

    cmd(config)
    assert jenkins.job_exists('trunktest')


#------------------------------------------------------------------------------
def test_nested_svnls(repo_nested):
    config = {
        'repo': repo_nested.url,
        'branches': [],
        'scm-username': None,
        'scm-password': None,
    }

    config['branches'] = [repo_nested.url + '/A/branches']
    assert svn.list_branches(config) == [
        'A/branches/1', 'A/branches/2', 'A/branches/3'
    ]

    config['branches'] = [repo_nested.url + '/*/branches']
    assert svn.list_branches(config) == [
        'A/branches/1', 'A/branches/2', 'A/branches/3',
        'B/branches/1', 'B/branches/2', 'B/branches/3',
        'C/branches/1', 'C/branches/2', 'C/branches/3',
        'D/branches/1', 'D/branches/2', 'D/branches/3',
    ]

    config['branches'] = [repo_nested.url + '/*/*/branches/']
    assert svn.list_branches(config) == [
        'sub1/A/branches/1', 'sub1/A/branches/2', 'sub1/A/branches/3',
        'sub1/B/branches/1', 'sub1/B/branches/2', 'sub1/B/branches/3',
        'sub1/C/branches/1', 'sub1/C/branches/2', 'sub1/C/branches/3',
        'sub1/D/branches/1', 'sub1/D/branches/2', 'sub1/D/branches/3',
        'sub2/A/branches/1', 'sub2/A/branches/2', 'sub2/A/branches/3',
        'sub2/B/branches/1', 'sub2/B/branches/2', 'sub2/B/branches/3',
        'sub2/C/branches/1', 'sub2/C/branches/2', 'sub2/C/branches/3',
        'sub2/D/branches/1', 'sub2/D/branches/2', 'sub2/D/branches/3'
    ]
