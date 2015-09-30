#!/usr/bin/env python
# -*- coding: utf-8; -*-

import re, copy
import subprocess as sub


#-----------------------------------------------------------------------------
def filtersplit(p, iterable):
    '''
    filtersplit(p, iter) -> ifilter(p, iter), ifilterfalse(p, iter)

    >>> iseven = lambda x: (x % 2) == 0
    >>> filtersplit(iseven, [0, 1, 2, 3, 4])
    ([0, 2, 4], [1, 3])
    '''

    t, f = [], []
    if p is None:
        p = bool

    for i in iterable:
        if p(i):
            t.append(i)
        else:
            f.append(i)

    return t, f

#-----------------------------------------------------------------------------
def pluralize(value):
    if not isinstance(value, list):
        return [value]
    return value

#-----------------------------------------------------------------------------
def anymatch(regexes, s):
    '''Return True if any of the regexes match the string.'''
    for r in regexes:
        if r.match(s):
            return True
    return False

#-----------------------------------------------------------------------------
def sanitize(ref, rules):
    '''
    >>> rules = {
    ...    '!?#&|\^_$%*': '_',
    ...    '/': '-',
    ...    '@': 'X',
    ...    're:develop': 'dev'
    ... }
    >>> sanitize('develop/test', rules)
    'dev-test'
    >>> sanitize('develop#test/zxcv@ASDF&1', rules)
    'dev_test-zxcvXASDF_1'
    '''
    for pattern, value in rules.items():
        if pattern.startswith('re:'):
            pattern = pattern.lstrip('re:')
        else:
            pattern = '|'.join(map(re.escape, pattern))
        ref = re.sub(pattern, value, ref)

    return ref

#-----------------------------------------------------------------------------
def merge(a, b):
    c = copy.copy(a)
    c.update(b)
    return c

#-----------------------------------------------------------------------------
# subprocess.check_output() from Python 2.7
def check_output(*popenargs, **kwargs):
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    process = sub.Popen(stdout=sub.PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        error = sub.CalledProcessError(retcode, cmd)
        error.output = output  # Compatibility with Python 2.6.
        raise error
    return output


#-----------------------------------------------------------------------------
if __name__ == "__main__":
    import doctest
    doctest.testmod()
