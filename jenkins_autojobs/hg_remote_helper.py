#!/usr/bin/env python
# -*- coding: utf-8; -*-

from __future__ import print_function

import sys
import time
import getopt

from mercurial import ui, hg, node


opts, args = getopt.getopt(sys.argv[1:], 'r:m:')
opts = dict(opts)

repo = opts['-r']
max_branch_age = opts.get('-m', 0)
max_branch_age = int(max_branch_age) * 24 * 3600

branches = []

peer = hg.peer(ui.ui(), {}, repo)
for name, rev in peer.branchmap().items():
    short_rev = node.short(rev[0])
    if max_branch_age:
        idx = peer.local().revs(short_rev).first()
        age = time.time() - peer.local()[idx].date()[0]
        if age > max_branch_age:
            continue

    branches.append((name, short_rev))

# This can be read back with ast.literal_eval().
print(repr(branches))
