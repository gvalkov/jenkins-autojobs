# -*- coding: utf-8; -*-

from pytest import fixture
from textwrap import dedent

from util import *
from jenkins_autojobs import hg
from jenkins import Jenkins, JenkinsError


#-----------------------------------------------------------------------------
# Fixtures and shortcuts.
cmd = partial(hg.main, ['jenkins-makejobs-hg'])

@fixture(scope='module')
def repo():
    repo = HgRepo()
    print('Creating temporary mercurial repo: %s' % repo.dir)
    repo.init()
    return repo

@fixture(scope='module')
def jenkins():
    print('Looking for a running Jenkins instance')
    webapi = Jenkins('http://127.0.0.1:60888')

    print('Removing all jobs ...')
    for job in webapi.jobs:
        webapi.job_delete(job.name)

    print('Creating test jobs ...')
    configxml = pjoin(here, 'etc/master-job-hg-config.xml')
    configxml = open(configxml).read().encode('utf8')
    webapi.job_create('master-job-hg', configxml)
    return webapi

@fixture(scope='function')
def config(jenkins, repo):
    base = '''
    jenkins: %s
    repo: %s

    template: master-job-hg

    namesep: '-'
    namefmt: 'changeme'
    overwrite: true
    enable: true

    python: /usr/bin/python2

    substitute :
      '@@JOB_NAME@@' : 'changeme'

    ignore:
      - 'branches/.*-nobuild'
      - 'experimental/bob/.*'

    refs:
      - 'branches/(.*)'
    '''

    base = dedent(base) % (jenkins.url, repo.url)
    base = yaml.load(StringIO(base))
    return base

@fixture(scope='function', autouse=True)
def cleanup(request, jenkins):
    def finalize():
        jobs = (job for job in jenkins.jobs if job.name != 'master-job-hg')
        for job in jobs:
            jenkins.job_delete(job.name)

    request.addfinalizer(finalize)

#------------------------------------------------------------------------------
params = [
    ['branches/feature-one',  '{branch}', '-', 'branches-feature-one'],
    ['branches/feature-two',  '{branch}', '-', 'branches-feature-two'],
    ['branches/feature-three', '{branch}', '.', 'branches.feature-three'],
]
@pytest.mark.parametrize(['branch', 'namefmt', 'namesep', 'expected'], params)
def test_namefmt_namesep_global(config, jenkins, repo, branch, namefmt, namesep, expected):
    config['namefmt'] = namefmt
    config['namesep'] = namesep
    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(expected)

#------------------------------------------------------------------------------
params = [
    ['branches/feature-one',   '{branch}',      '.',           'branches.feature-one'],
    ['branches/feature-two',   'test.{branch}', 'X', 'test.branchesXfeature-two'],
    ['branches/feature-three', 'test.{branch}', '_', 'test.branches_feature-three'],
]
@pytest.mark.parametrize(['branch', 'namefmt', 'namesep', 'expected'], params)
def test_namefmt_namesep_inherit(config, jenkins, repo, branch, namefmt, namesep, expected):
    config['refs'] = [ {branch: {
        'namesep': namesep,
        'namefmt': namefmt, }}]

    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(expected)

#------------------------------------------------------------------------------
params = [
    ['experimental/john/bug/01', 'experimental/(.*)/bug/(.*)', '{0}-{1}', 'john-01'],
    ['tag/alpha/gamma',          '(.*)/(.*)/(.*)', 'test-{2}.{1}.{0}', 'test-gamma.alpha.tag'],
]
@pytest.mark.parametrize(['branch', 'regex', 'namefmt', 'expected'], params)
def test_namefmt_groups_inherit(config, jenkins, repo, branch, regex, namefmt, expected):
    config['namefmt'] = '.'
    config['refs'] = [ {regex: {'namefmt' : namefmt}} ]
    config['refs'].append(os.path.join(config['repo'], os.path.dirname(branch)))

    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(expected)

#------------------------------------------------------------------------------
params = [
    ['branches/alpha', '{repo}/branches/alpha',  '.']
]
@pytest.mark.parametrize(['branch', 'name', 'local'], params)
def test_configxml_global(config, jenkins, repo, branch, name, local):
    job = branch.replace('/', '-')
    name = name.format(**config)

    config['namefmt'] = '{branch}'
    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(job)
        configxml = jenkins.job_config_etree(job)
        scm_el = configxml.xpath('scm[@class="hudson.plugins.mercurial.MercurialSCM"]')[0]
        el = scm_el.xpath('//branch')[0]
        assert el.text == branch

#------------------------------------------------------------------------------
def test_cleanup(config, jenkins, repo):
    config['cleanup'] = True
    config['namefmt'] = '{branch}'
    config['namesep'] = '-'

    with repo.branches('branches/one', 'branches/two'):
        cmd(config)

        assert jenkins.job_exists('branches-one')
        assert jenkins.job_exists('branches-two')
        assert 'createdByJenkinsAutojobs' in jenkins.job('branches-one').config

    with repo.branch('branches/one'):
        cmd(config)
        assert not jenkins.job_exists('branches-two')
