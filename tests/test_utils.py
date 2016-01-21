# -*- coding: utf-8; -*-

import re

from jenkins_autojobs import main


def test_filter_jobs():
    class Job:
        def __init__(self, name):
            self.name = name

    class jenkins:
        @staticmethod
        def view_jobs(x):
            return {
                'v1': [Job('scratch-one'), Job('scratch-two')],
                'v2': [Job('release-one'), Job('maintenance-three')]
            }[x]

    names = ['feature-one', 'feature-two', 'release-one', 'release-two']
    jenkins.jobs = [Job(i) for i in names]
    filter_jobs = lambda **kw: {i.name for i in main.filter_jobs(jenkins, **kw)}

    #-------------------------------------------------------------------------
    assert filter_jobs() == {'feature-one', 'feature-two', 'release-one', 'release-two'}

    res = filter_jobs(by_name_regex=[re.compile('feature-')])
    assert res == {'feature-one', 'feature-two'}

    res = filter_jobs(by_name_regex=[re.compile('.*one'), re.compile('.*two')])
    assert res == {'feature-one', 'feature-two', 'release-one', 'release-two'}

    #-------------------------------------------------------------------------
    res = filter_jobs(by_views=['v1'])
    assert res == {'scratch-one', 'scratch-two'}

    res = filter_jobs(by_views=['v1', 'v2'])
    assert res == {'scratch-one', 'scratch-two', 'release-one', 'maintenance-three'}
