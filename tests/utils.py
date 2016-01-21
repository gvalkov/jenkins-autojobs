# -*- coding: utf-8; -*-


def is_created_by_jenkinsautojobs(job, tag_method='description'):
    if tag_method == 'element':
        return 'createdByJenkinsAutojobs' in job.config
    elif tag_method == 'description':
        return '(created by jenkins-autojobs)' in job.info['description']
