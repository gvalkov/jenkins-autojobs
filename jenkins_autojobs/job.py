# -*- coding: utf-8; -*-

from __future__ import absolute_import

import copy
import lxml.etree

from xml.sax.saxutils import escape as xmlescape
from . import utils


class Job(object):
    def __init__(self, name, branch, template, jenkins):
        self.name = name
        self.branch = branch  # the scm branch that this job builds
        self.jenkins = jenkins

        # This will be the new config.xml for the job we're creating.
        self.xml = copy.deepcopy(template)

        # This is the raw config xml of the job  :todo: naming is mixed-up.
        job = jenkins.job(name)
        self.exists = job.exists
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
            if '<disabled>true</disabled>' in self.config:
                el.text = 'true'

    def substitute(self, items, fmtdict, groups, groupdict):
        for el in self.xml.xpath("//text()"):
            for k, v in items:
                if k in el:
                    p = el.getparent()
                    ctx = utils.merge(groupdict, fmtdict)
                    nv = p.text.replace(k, v.format(*groups, **ctx))
                    p.text = nv

    def canonicalize(self, xml):
        try:
            return lxml.etree.tostring(xml, method='c14n')
        except ValueError:
            # Installed lxml does not support c14n.
            return lxml.etree.tostring(xml)

    def tag_config(self, tag=None, method='description'):
        if method == 'description':
            mark = '\n(created by jenkins-autojobs)'
            tag = ('\n(jenkins-autojobs-tag: %s)' % tag) if tag else ''

            mark = xmlescape(mark)
            tag  = xmlescape(tag)
            desc_el = Job.find_or_create_description_el(self.xml)

            if desc_el.text is None:
                desc_el.text = ''
            if mark not in desc_el.text:
                desc_el.text += mark
            if tag not in desc_el.text:
                desc_el.text += tag

        elif method == 'element':
            info_el = lxml.etree.SubElement(self.xml, 'createdByJenkinsAutojobs')
            ref_el  = lxml.etree.SubElement(info_el, 'ref')
            ref_el.text = xmlescape(self.branch)

            # Tag builds.
            if tag:
                tag_el = lxml.etree.SubElement(info_el, 'tag')
                tag_el.text = xmlescape(tag)

    def create(self, overwrite, build_on_create, dryrun, tag=None, tag_method='description'):
        # Mark build as created by jenkins-autojobs and add tags.
        self.tag_config(tag, tag_method)

        # method='c14n' is only available in more recent versions of lxml
        self.xml = self.canonicalize(self.xml)

        if self.exists and overwrite:
            job_config_dom = lxml.etree.fromstring(self.config.encode('utf8'))

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

            # Build newly created job.
            if build_on_create:
                if not dryrun:
                    self.jenkins.job_build(self.name)
                print('. build triggered')

        elif not overwrite:
            print('. overwrite disabled - skipping job')

    @staticmethod
    def find_or_create_description_el(xml):
        parent, description = Job.find_description_el(xml)

        if not description and parent is None:
            msg = 'cannot determine project type and the location of the description element'
            raise RuntimeError(msg)

        if not description:
            description = lxml.etree.Element('description')
            parent.insert(1, description)
        else:
            description = description[0]
        return description

    @staticmethod
    def find_description_el(xml):
        # The location of the project description element depends on the type
        # of project.
        for parent_xpath in '//maven2-moduleset', '//project':
            parent = xml.xpath(parent_xpath)
            if not parent:
                continue
            desc_xpath = parent_xpath + '/description'
            return parent[0], xml.xpath(desc_xpath)

        # The next best thing to try is to look for the first description
        # element in the document.
        description = xml.xpath('//description')
        return None, description
