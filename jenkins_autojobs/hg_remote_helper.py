#!/usr/bin/env python
# -*- coding: utf-8; -*-

from __future__ import print_function

import sys
import getopt

from mercurial import ui, hg, node


opts, args = getopt.getopt(sys.argv[1:], 'r:m:')
opts = dict(opts)
repo = opts['-r']

branches = []
peer = hg.peer(ui.ui(), {}, repo)

for name, rev in peer.branchmap().items():
    branches.append((name, node.short(rev[0])))

# This can be read back with ast.literal_eval().
print(repr(branches))
