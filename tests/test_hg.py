from util import *
from jenkins_autojobs import hg


jenkins = j = None
jobexists = None
repo = r = HgRepo()

cmd = partial(hg.main, ('jenkins-makejobs-hg',))

base_config_dict = None
base_config_yaml = '''
jenkins: {url}
repo: {repo}

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


def setup_module(module):
    # print('Starting Jenkins ...')
    # j.start_server()

    global jenkins, j, jobexists
    global base_config_dict

    print('Looking for a running Jenkins instance')
    jenkins = j = JenkinsControl('127.0.0.1:60888', '60887')
    jobexists = partial(jenkins.py.job_exists)

    base_config_dict = yaml.load(StringIO(base_config_yaml.format(url=j.url, repo=r.url)))
    base_config_dict['namefmt'] = '{branch}'

    print('Removing all jobs ...')
    for job in j.getjobs():
        j.py.job_delete(job)

    print('Creating test jobs ...')
    j.createjob('master-job-hg', pjoin(here, 'etc/master-job-hg-config.xml'))

    print('Creating temporary hg repo: %s' % repo.dir)
    repo.init()

def teardown_module(module):
    teardown_module_(module, jenkins, repo)

def teardown_function(f):
    teardown_function_(f, jenkins)

def pytest_funcarg__cfg(request):
    return deepcopy(base_config_dict)


@pytest.mark.parametrize(('branch', 'namefmt', 'namesep', 'expected'), [
('branches/feature-one',  '{branch}', '-', 'branches-feature-one'),
('branches/feature-two',  '{branch}', '-', 'branches-feature-two'),
('branches/feature-three', '{branch}', '.', 'branches.feature-three'), ])
def test_namefmt_namesep_global(cfg, branch, namefmt, namesep, expected):
    test_namefmt_namesep_global.cleanup_jobs = [expected]

    cfg['namefmt'] = namefmt
    cfg['namesep'] = namesep
    with r.branch(branch):
        cmd(cfg)
        assert jobexists(expected)

@pytest.mark.parametrize(('branch', 'namefmt', 'namesep', 'expected'),[
('branches/feature-one',   '{branch}',      '.',           'branches.feature-one'),
('branches/feature-two',   'test.{branch}', 'X', 'test.branchesXfeature-two'),
('branches/feature-three', 'test.{branch}', '_', 'test.branches_feature-three'), ])
def test_namefmt_namesep_inherit(cfg, branch, namefmt, namesep, expected):
    test_namefmt_namesep_inherit.cleanup_jobs = [expected]

    cfg['refs'] = [ {branch : {
        'namesep' : namesep,
        'namefmt' : namefmt, }}]

    with r.branch(branch):
        cmd(cfg)
        assert jobexists(expected)

@pytest.mark.parametrize(('branch', 'regex', 'namefmt', 'expected'),[
('experimental/john/bug/01', 'experimental/(.*)/bug/(.*)', '{0}-{1}', 'john-01'),
('tag/alpha/gamma',          '(.*)/(.*)/(.*)', 'test-{2}.{1}.{0}', 'test-gamma.alpha.tag'), ])
def test_namefmt_groups_inherit(cfg, branch, regex, namefmt, expected):
    test_namefmt_groups_inherit.cleanup_jobs = [expected]

    cfg['namefmt'] = '.'
    cfg['refs'] = [{ regex : {'namefmt' : namefmt, }}]
    cfg['refs'].append(os.path.join(cfg['repo'], os.path.dirname(branch)))

    with r.branch(branch):
        cmd(cfg)
        assert jobexists(expected)

@pytest.mark.parametrize(('branch', 'name', 'local'),[
('branches/alpha', '{repo}/branches/alpha',  '.'),])
def test_configxml_global(cfg, branch, name, local):
    job = branch.replace('/', '-')
    test_configxml_global.cleanup_jobs = [job]
    name = name.format(**cfg)

    with r.branch(branch):
        cmd(cfg)
        assert jobexists(job)

        configxml = jenkins.job_etree(job)

        scm_el = configxml.xpath('scm[@class="hudson.plugins.mercurial.MercurialSCM"]')[0]
        el = scm_el.xpath('//branch')[0]
        assert el.text == branch
