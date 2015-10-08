# -*- coding: utf-8; -*-

import time, copy
import io, yaml, pytest

from pytest import mark
from pytest import fixture, yield_fixture
from textwrap import dedent
from functools import partial

from repo_fixture import repo_fixture
from jenkins_autojobs import git, main
from jenkins import Jenkins


#-----------------------------------------------------------------------------
# Fixtures and shortcuts.
cmd = partial(git._main, ['jenkins-makejobs-git'])

@yield_fixture(scope='module')
def repo():
    r = repo_fixture('git')
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
    configxml = 'master-job-git-config.xml'
    configxml = open(configxml).read().encode('utf8')
    webapi.job_create('master-job-git', configxml)
    return webapi

@fixture(scope='module')
def view(request, jenkins):
    if jenkins.view_exists('Tests'):
        jenkins.view_delete('Tests')

    configxml = 'test-view-config.xml'
    jenkins.view_create('Tests', open(configxml).read().encode('utf8'))
    request.addfinalizer(lambda: jenkins.view_delete('Tests'))
    return 'Tests'

@fixture(scope='function')
def config(jenkins, repo):
    base = u'''
    jenkins: %s
    repo: %s

    template: master-job-git
    namesep: '-'
    namefmt: '{shortref}'
    overwrite: true
    enable: 'sticky'

    sanitize:
      '@!?#&|\^_$%%*': '_'

    substitute:
      '@@JOB_NAME@@': '{shortref}'

    ignore:
      - 'refs/heads/feature/.*-nobuild'

    refs:
      - 'refs/heads/feature/(.*)'
      - 'refs/heads/scratch/(.*)':
          'namefmt': '{shortref}'
    '''

    base = dedent(base) % (jenkins.url, repo.url)
    base = yaml.load(io.StringIO(base))
    return base

@fixture(scope='function', autouse=True)
def cleanup(request, jenkins):
    def finalize():
        jobs = (job for job in jenkins.jobs if job.name != 'master-job-git')
        for job in jobs:
            jenkins.job_delete(job.name)

    request.addfinalizer(finalize)


#-----------------------------------------------------------------------------
params = [
    ['feature/one/two', '{shortref}',      '.', 'feature.one.two'],
    ['feature/one/two', 'test-{shortref}', '-', 'test-feature-one-two'],
    ['feature/one/two', 'test.{ref}',      '-', 'test.refs-heads-feature-one-two'],
]
@mark.parametrize(['branch', 'namefmt', 'namesep', 'expected'], params)
def test_namefmt_namesep_global(config, jenkins, repo, branch, namefmt, namesep, expected):
    config['namefmt'] = namefmt
    config['namesep'] = namesep

    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(expected)


#-----------------------------------------------------------------------------
params = [
    ['feature/one/two', '{shortref}',      '.', 'feature.one.two'],
    ['feature/one/two', 'test-{shortref}', '-', 'test-feature-one-two'],
    ['feature/one/two', 'test.{ref}',      '-', 'test.refs-heads-feature-one-two'],
]
@mark.parametrize(['branch', 'namefmt', 'namesep', 'expected'], params)
def test_namefmt_namesep_global(config, jenkins, repo, branch, namefmt, namesep, expected):
    config['namefmt'] = namefmt
    config['namesep'] = namesep

    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(expected)


#-----------------------------------------------------------------------------
params = [
    ['scratch/one/two', '{shortref}', '.', 'scratch.one.two'],
    ['scratch/one/two', 'test.{ref}', '_', 'test.refs_heads_scratch_one_two'],
    ['scratch/one/two', 'test.{shortref}', '_', 'test.scratch_one_two'],
]
@mark.parametrize(['branch', 'namefmt', 'namesep', 'expected'], params)
def test_namefmt_namesep_inherit(config, jenkins, repo, branch, namefmt, namesep, expected):
    config['refs'] = [{
        'refs/heads/%s' % branch : {
            'namesep': namesep,
            'namefmt': namefmt,
        }
    }]

    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(expected)


#-----------------------------------------------------------------------------
params = [
    ['feature/one@two', '{shortref}',      {'#@': 'X'}, '.', 'feature.oneXtwo'],
    ['feature/one#two', 'test-{shortref}', {'#@': '_'}, '-', 'test-feature-one_two'],
    ['feature/one@#two','test.{ref}',      {'#@': '_'}, '-', 'test.refs-heads-feature-one__two'],
]
@mark.parametrize(['branch', 'namefmt', 'sanitize', 'namesep', 'expected'], params)
def test_namefmt_sanitize_global(config, jenkins, repo, branch, namefmt, sanitize, namesep, expected):
    config['namefmt'] = namefmt
    config['namesep'] = namesep
    config['sanitize'] = sanitize

    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(expected)


#-----------------------------------------------------------------------------
params = [
    ['feature/one#two', '{shortref}',      {'#': '_'}, '.', 'feature.one_two'],
    ['feature/one#two@three','test.{ref}', {'#@': '_'}, '-', 'test.refs-heads-feature-one_two_three'],
]
@mark.parametrize(['branch', 'namefmt', 'sanitize', 'namesep', 'expected'], params)
def test_namefmt_sanitize_inherit(config, jenkins, repo, branch, namefmt, sanitize, namesep, expected):
    config['namefmt'] = namefmt
    config['namesep'] = namesep
    config['sanitize'] = {'#': 'X'}

    config['refs'] = [{
        'refs/heads/%s' % branch : {
            'sanitize' : sanitize,
        }}]

    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(expected)


#-----------------------------------------------------------------------------
params = [
    ['scratch/one/two/three', 'refs/heads/scratch/(.*)/(.*)/', '{0}-wip-{1}', 'one-wip-two'],
    ['scratch/one/two/three', 'refs/heads/scratch/(.*)/.*/(.*)', '{1}.{0}', 'three.one'],
    ['wip/alpha/beta/gamma',  'refs/heads/wip/(.*)/.*/(.*)', 'test-{1}.{0}', 'test-gamma.alpha'],
]
@mark.parametrize(['branch', 'regex', 'namefmt', 'expected'], params)
def test_namefmt_groups_inherit(config, jenkins, repo, branch, regex, namefmt, expected):
    config['namefmt'] = '.'
    config['refs'] = [{ regex: {'namefmt' : namefmt, }}]

    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(expected)


#-----------------------------------------------------------------------------
params = [
    ['feature/one/two',   {'@@JOB_NAME@@' : '{shortref}'}, 'feature-one-two', 'feature-one-two'],
    ['feature/two/three', {'@@JOB_NAME@@' : 'one-{ref}'},  'feature-two-three', 'one-refs-heads-feature-two-three'],
]
@mark.parametrize(['branch', 'sub', 'ejob', 'expected'], params)
def test_substitute(config, jenkins, repo, branch, sub, ejob, expected):
    test_substitute.cleanup_jobs = [ejob]
    config['substitute'] = sub

    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(ejob)
        assert jenkins.job_info(ejob)['description'] == expected

def test_substitute_reposub(config, jenkins, repo):
    config['substitute'] = {'@@JOB_NAME@@': '{repo-orig}'}
    with repo.branch('feature/reposub'):
        cmd(config)
        assert jenkins.job_exists('feature-reposub')
        assert jenkins.job_info('feature-reposub')['description'] == config['repo']

#-----------------------------------------------------------------------------
def test_substitute_groups(config, jenkins, repo):
    config['refs'] = ['refs/heads/(?P<type>(?:feature|release))/(.*)/(.*)']
    with repo.branch('feature/one/two.three') as name:
        cmd(config)
        assert jenkins.job_exists('feature-one-two.three')

    config['substitute'] = {'@@JOB_NAME@@' : '{2}'}
    config['refs'] = ['refs/heads/release-((?:(\d+\.){1,2})[1-9]+\d*)-(.*)']
    with repo.branch('release-0.7.4-wheezy') as name:
        cmd(config)
        assert jenkins.job_info(name)['description'] == 'wheezy'

    config['refs'] = ['refs/heads/feature-(\d\d)-(?P<name>\w+)-(\d)']
    config['substitute'] = {'@@JOB_NAME@@' : '{0}-{name}-{2}'}
    with repo.branch('feature-55-random-1') as name:
        cmd(config)
        assert jenkins.job_info(name)['description'] == '55-random-1'


#-----------------------------------------------------------------------------
params = [
    ['wip/one/two',  ['wip/.*']],
    ['feature/zetta-nobuild', ['.*-nobuild']]
]
@mark.parametrize(['branch', 'ignores'], params)
def test_ignore(config, jenkins, repo, branch, ignores):
    job = branch.replace('/', config['namesep'])

    config['ignore'] = ignores
    with repo.branch(branch):
        cmd(config)
        assert not jenkins.job_exists(job)


#-----------------------------------------------------------------------------
params = [
    ['feature/config-one', 'origin/refs/heads/feature/config-one', 'feature/config-one']
]
@mark.parametrize(['branch', 'name', 'local'], params)
def test_configxml_global(config, jenkins, repo, branch, name, local):
    job = branch.replace('/', config['namesep'])
    test_configxml_global.cleanup_jobs = [job]

    with repo.branch(branch):
        cmd(config)
        assert jenkins.job_exists(job)

        configxml = jenkins.job_config_etree(job)

        scm_el = configxml.xpath('scm[@class="hudson.plugins.git.GitSCM"]')[0]
        el = scm_el.xpath('//hudson.plugins.git.BranchSpec/name')[0]
        assert el.text == local
        assert scm_el.xpath('//localBranch')[0].text == local


#-----------------------------------------------------------------------------
def test_overwrite_global(config, jenkins, repo, capsys):
    config['overwrite'] = False
    config['namefmt'] = 'samename'

    with repo.branch('feature/one'):
        cmd(config)
        assert jenkins.job_exists('samename')

    with repo.branch('feature/one'):
        cmd(config)
        assert jenkins.job_exists('samename')

        # :todo: find better way
        out, err = capsys.readouterr()
        assert 'create job' not in out


#-----------------------------------------------------------------------------
def test_enable_true(config, jenkins, repo,):
    jenkins.job_disable('master-job-git')
    config['enable'] = True

    with repo.branch('feature/enable-true'):
        cmd(config)
        assert jenkins.job_exists('feature-enable-true')


#-----------------------------------------------------------------------------
def test_enable_false(config, jenkins, repo,):
    jenkins.job_enable('master-job-git')
    config['enable'] = False

    with repo.branch('feature/enable-false'):
        cmd(config)
        assert jenkins.job_exists('feature-enable-false')
        assert not jenkins.job_enabled('feature-enable-false')


#-----------------------------------------------------------------------------
def test_enable_template(config, jenkins, repo,):
    config['enable'] = 'template'

    jenkins.job_enable('master-job-git')
    with repo.branch('feature/enable-template-one'):
        cmd(config)
        assert jenkins.job_exists('feature-enable-template-one')
        assert jenkins.job_enabled('feature-enable-template-one')

    jenkins.job_disable('master-job-git')
    with repo.branch('feature/enable-template-two'):
        cmd(config)
        assert jenkins.job_exists('feature-enable-template-two')
        assert not jenkins.job_enabled('feature-enable-template-two')


#-----------------------------------------------------------------------------
def test_enable_sticky(config, jenkins, repo):
    config['enable'] = 'sticky'
    config['overwrite'] = True

    # First run inherits the enabled state of the template job.
    jenkins.job_disable('master-job-git')
    with repo.branch('feature/enable-sticky-one'):
        cmd(config)
        assert not jenkins.job_enabled('feature-enable-sticky-one')

    # If child job is enabled, it will remain enabled.
    jenkins.job_enable('feature-enable-sticky-one')
    cmd(config)
    assert jenkins.job_enabled('feature-enable-sticky-one')

    jenkins.job_disable('feature-enable-sticky-one')
    cmd(config)
    assert not jenkins.job_enabled('feature-enable-sticky-one')

    #-------------------------------------------------------------------------
    jenkins.job_enable('master-job-git')
    with repo.branch('feature/enable-sticky-two'):
        cmd(config)
        assert jenkins.job_enabled('feature-enable-sticky-two')

    # If child job is disabled, it will remain disabled.
    jenkins.job_disable('feature-enable-sticky-two')
    cmd(config)
    assert not jenkins.job_enabled('feature-enable-sticky-two')


#-----------------------------------------------------------------------------
def test_inheritance_order(config, jenkins, repo):
    config['refs'] = [
        { 'refs/heads/feature/bravo/(.*)' : {'namefmt' : 'one-{shortref}'} },
        { 'refs/heads/feature/(.*)'       : {'namefmt' : 'two-{shortref}'} },
    ]

    with repo.branch('feature/bravo/four'):
        cmd(config)
        assert jenkins.job_exists('one-feature-bravo-four')


#-----------------------------------------------------------------------------
def test_missing_template(config, jenkins, repo):
    config['template'] = 'does-not-exist'
    with pytest.raises(SystemExit):
        cmd(config)


#-----------------------------------------------------------------------------
def test_cleanup(config, jenkins, repo):
    config['cleanup'] = True

    with repo.branches('feature/one', 'feature/two'):
        cmd(config)
        assert jenkins.job_exists('feature-one')
        assert jenkins.job_exists('feature-two')
        assert 'createdByJenkinsAutojobs' in jenkins.job('feature-one').config

    with repo.branch('feature/one'):
        cmd(config)
        assert not jenkins.job_exists('feature-two')


#-----------------------------------------------------------------------------
def test_failing_git_cleanup(config, jenkins, repo):
    config['cleanup'] = True

    with repo.branches('feature/one', 'feature/two'):
        cmd(config)
        assert jenkins.job_exists('feature-one')
        assert jenkins.job_exists('feature-two')
        assert 'createdByJenkinsAutojobs' in jenkins.job('feature-one').config

        config['repo'] = '/tmp/should-never-exist-zxcv-123-zxcv-1asfmn'
        with pytest.raises(SystemExit):
            cmd(config)
        # feature-{one,two} should not be removed if command fails
        assert jenkins.job_exists('feature-one')
        assert jenkins.job_exists('feature-two')


#-----------------------------------------------------------------------------
def test_tag_element(config, jenkins, repo):
    config['tag'] = 'group1'
    config['tag-method'] = 'element'
    config['refs'] = [
        {'refs/heads/feature/(.*)': {'namefmt': '{shortref}'}},
        {'refs/heads/test': {'tag': 'group2'}},
    ]

    with repo.branch('feature/one'):
        cmd(config)
        jobc = jenkins.job('feature-one').config
        assert main.get_autojobs_tags(jobc, 'element') == ['group1']
        assert '<tag>group1</tag>' in jobc

    with repo.branch('test'):
        cmd(config)
        assert '<tag>group2</tag>' in jenkins.job('test').config

def test_tag_description(config, jenkins, repo):
    config['tag'] = 'group1'
    config['tag-method'] = 'description'
    config['refs'] = [
        {'refs/heads/feature/(.*)': {'namefmt': '{shortref}'}},
        {'refs/heads/test': {'tag': 'group2'}},
    ]

    with repo.branch('feature/one'):
        cmd(config)
        job = jenkins.job('feature-one')
        desc = job.config_etree.xpath('/project/description/text()')[0]
        assert '\n(created by jenkins-autojobs)' in desc
        assert '\n(jenkins-autojobs-tag: group1)' in desc
        assert main.get_autojobs_tags(job.config, 'description') == ['group1']

    with repo.branch('feature/one'):
        cmd(config)
        job = jenkins.job('feature-one')
        main.get_autojobs_tags(jenkins.job('feature-one').config, 'description')


#-----------------------------------------------------------------------------
def test_cleanup_filter_regex(config, jenkins, repo):
    config['cleanup'] = True

    config['cleanup-filters'] = {
        'jobs': ['.*one']
    }

    with repo.branches('feature/one', 'feature/one1', 'feature/two'):
        cmd(copy.deepcopy(config))

    with repo.branch('feature/one'):
        cmd(copy.deepcopy(config))
        assert not jenkins.job_exists('feature-one1')
        assert jenkins.job_exists('feature-two')

def test_cleanup_filter_view(config, jenkins, view, repo):
    config['cleanup'] = True

    with repo.branches('feature/three'):
        cmd(copy.deepcopy(config))

    config['view'] = [view]
    config['cleanup-filters'] = {
        'views': [view]
    }

    with repo.branches('feature/one', 'feature/one1', 'feature/two'):
        cmd(copy.deepcopy(config))

    with repo.branch('feature/one'):
        cmd(copy.deepcopy(config))
        assert not jenkins.job_exists('feature-one1')
        assert not jenkins.job_exists('feature-two')
        assert jenkins.job_exists('feature-three')


#-----------------------------------------------------------------------------
@mark.parametrize('tag_method', ['element', 'description'])
def test_cleanup_tags(config, jenkins, repo, tag_method):
    config['cleanup'] = 'group1'
    config['tag-method'] = tag_method
    config['refs'] = [
        {'refs/heads/group1/(.*)': {'tag': 'group1'}},
        {'refs/heads/group2/(.*)': {'tag': 'group2'}},
    ]

    with repo.branches('group1/one', 'group1/two', 'group2/three'):
        cmd(config)
        assert jenkins.job_exists('group1-one')
        assert jenkins.job_exists('group1-two')
        assert jenkins.job_exists('group2-three')

    cmd(config)
    assert not jenkins.job_exists('group1-one')
    assert not jenkins.job_exists('group1-two')
    assert jenkins.job_exists('group2-three')

    config['cleanup'] = 'group2'
    with repo.branches('group1/one'):
        cmd(config)
        assert not jenkins.job_exists('group2-three')


#-----------------------------------------------------------------------------
def test_views(config, jenkins, view, repo):
    config['namefmt'] = '{shortref}'
    config['view'] = [view, 'All']  # All should be filtered out in main()

    with repo.branches('feature/one'):
        cmd(config)
        assert '<string>feature-one</string>' in jenkins.view_config(view)


#-----------------------------------------------------------------------------
def test_views_nonexist(config, jenkins, repo):
    config['namefmt'] = '{shortref}'
    config['view'] = ['abc', 'zxc']

    with pytest.raises(SystemExit):
        cmd(config)


#-----------------------------------------------------------------------------
@mark.slow
def test_build_on_create(config, jenkins, repo):
    config['build-on-create'] = True

    with repo.branches('feature/one'):
        cmd(config)
        time.sleep(10)
        assert len(jenkins.job('feature-one').builds) == 1
