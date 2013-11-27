from copy import deepcopy
from lxml import etree


class Job(object):
    def __init__(self, name, template, jenkins):
        self.name = name
        self.jenkins = jenkins

        # this will be the new config.xml for the job we're creating
        self.xml = deepcopy(template)

        # this is the raw config xml of the job  :todo: naming is mixed-up
        job = jenkins.job(name)
        self.exists = job.exists()
        self.config = job.config if self.exists else None

    def set_state(self, value):
        '''Set the state of newly created or overwritten job. One of:
             True  -> Jobs will be enabled
             False -> Jobs will be disabled
             'template' -> Jobs will inherit the state of the template jobs
             'sticky'   -> New jobs inherit the state of the template job.
                           Overwritten jobs keep their previous state.
        '''
        el = self.xml.xpath('disabled')[0]

        if value is True or value == 'true':
            el.text = 'false'
        elif value is False or value == 'false':
            el.text = 'true'
        elif value == 'template':
            pass
        elif value == 'sticky' and self.config:
            if '<disabled>false</disabled>' in self.config:
                el.text = 'false'

    def substitute(self, items, fmtdict):
        for el in self.xml.xpath("//text()"):
            for k, v in items:
                if k in el:
                    p = el.getparent()
                    nv = p.text.replace(k, v.format(**fmtdict))
                    p.text = nv

    def canonicalize(self, xml):
        try:
            return etree.tostring(xml, method='c14n')
        except ValueError:
            # Guess the installed lxml is too old to support c14n.
            # Drat. Unable to canonicalize the xml, so hopefully
            # nobody makes a non-semantic change...
            return etree.tostring(xml)

    def create(self, overwrite, dryrun):
        # method='c14n' is only available in more recent versions of lxml
        self.xml = self.canonicalize(self.xml)

        if self.exists and overwrite:
            job_config_dom = etree.fromstring(self.config.encode('utf8'))

            if self.canonicalize(job_config_dom) == self.xml:
                print('. job does not need to be reconfigured')
                return

            if not dryrun:
                job = self.jenkins.job(self.name)
                job.config = self.xml
            print('. job updated')

        elif not self.exists:
            if not dryrun:
                self.jenkins.job_create(self.name, self.xml)
            print('. job created')

        elif not overwrite:
            print('. overwrite disabled - skipping job')
