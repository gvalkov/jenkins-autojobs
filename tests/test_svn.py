from util import *
from jenkins_autojobs import svn


jenkins = j = None
jobexists = None
repo = r = SvnRepo()

cmd = partial(svn.main, ('jenkins-makejobs-svn',))

base_config_dict = None
base_config_yaml = '''
jenkins: {url}
repo: {repo}

trunk: file://{repo}/trunk/
branches:
  - {repo}/branches/
  - {repo}/experimental/

template: master-job-svn

namesep: '-'
namefmt: 'changeme'
overwrite: true
enable: true

substitute :
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
    j.createjob('master-job-svn', pjoin(here, 'etc/master-job-svn-config.xml'))

    print('Creating temporary svn repo: %s' % repo.dir)
    repo.init()

def teardown_module(module):
    teardown_module_(module, jenkins, repo)

def teardown_function(f):
    teardown_function_(f, jenkins)

def pytest_funcarg__cfg(request):
    return deepcopy(base_config_dict)


@pytest.mark.parametrize(('branch', 'namefmt', 'namesep', 'expected'), [
('branches/feature-one', '{branch}', '-', 'feature-one'),
('branches/feature-one', '{path}',   '-', 'branches-feature-one'),
('branches/feature-one', '{path}',   '.', 'branches.feature-one'), ])
def test_namefmt_namesep_global(cfg, branch, namefmt, namesep, expected):
    test_namefmt_namesep_global.cleanup_jobs = [expected]

    cfg['namefmt'] = namefmt
    cfg['namesep'] = namesep
    with r.branch(branch):
        cmd(cfg)
        assert jobexists(expected)

@pytest.mark.parametrize(('branch', 'namefmt', 'namesep', 'expected'),[
('branches/feature-two', '{branch}',    '.', 'feature-two'),
('branches/feature-two', 'test.{path}', 'X', 'test.branchesXfeature-two'),
('branches/feature-two', 'test.{path}', '_', 'test.branches_feature-two'), ])
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

    cfg['branches'].append(os.path.join(cfg['repo'], os.path.dirname(branch)))
    cfg['namefmt'] = '.'
    cfg['refs'] = [{ regex : {'namefmt' : namefmt, }}]

    with r.branch(branch):
        cmd(cfg)
        assert jobexists(expected)

@pytest.mark.parametrize(('branch', 'ignores'),[
('experimental/john',  ['experimental/.*']),
('experimental/v0.1-nobuild', ['.*-nobuild'])])
def test_ignore(cfg, branch, ignores):
    test_ignore.cleanup_jobs = [branch.replace('/', cfg['namesep'])]

    cfg['ignore'] = ignores
    with r.branch(branch):
        cmd(cfg)
        assert not jobexists(test_ignore.cleanup_jobs[0])

@pytest.mark.parametrize(('branch', 'name', 'local'),[
('branches/alpha', '{repo}/branches/alpha',  '.'),])
def test_configxml_global(cfg, branch, name, local):
    job = branch.split('/')[-1]
    test_configxml_global.cleanup_jobs = [job]
    name = name.format(**cfg)

    with r.branch(branch):
        cmd(cfg)
        assert jobexists(job)

        configxml = jenkins.job_etree(job)

        scm_el = configxml.xpath('scm[@class="hudson.scm.SubversionSCM"]')[0]
        el = scm_el.xpath('//remote')[0]
        assert el.text == name

        assert scm_el.xpath('//local')[0].text == local

@cleanup('one')
def test_cleanup(cfg):
    cfg['cleanup'] = True

    with r.branches('branches/one', 'branches/two'):
        cmd(cfg)
        assert jobexists('one')
        assert jobexists('two')
        assert 'createdByJenkinsAutojobs' in j.py.job('one').config

    with r.branch('branches/one'):
        cmd(cfg)
        assert not jobexists('two')
