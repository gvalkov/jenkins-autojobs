import re


def filtersplit(p, iterable):
    ''' filtersplit(p, iter) -> ifilter(p, iter), ifilterfalse(p, iter)'''
    t, f = [], []
    if p is None: p = bool
    for i in iterable:
        if p(i): t.append(i)
        else: f.append(i)
    return t, f

def anymatch(regexes, s):
    for r in regexes:
        if r.match(s): return True
    return False
