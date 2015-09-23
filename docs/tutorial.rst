Tutorial
========

This tutorial goes over the steps of installing and configuring
jenkins-autojobs.


Installing
----------

The latest stable version of jenkins-autojobs can be installed from pypi_
using pip.

.. code-block:: bash

    $ pip install jenkins-autojobs

Jenkins-autojobs depends on a version of lxml with support for XML
canonicalization (c14n). Setup will attempt to install one if it is not
present on your system. You might have to install the ``libxml`` and
``libxslt`` development headers if you haven't already done so:

On a Debian compatible OS:

.. code-block:: bash

    $ apt-get install libxml2-dev libxslt1-dev

On a Redhat compatible OS:

.. code-block:: bash

    $ yum install libxml2-devel libxslt-devel

On Arch Linux or derivatives:

.. code-block:: bash

    $ pacman -S libxslt libxml2


Usage
-----

If jenkins-autojobs was installed succesfully, you'll find that there are
three new scripts on your system:

 - ``jenkins-makejobs-git``
 - ``jenkins-makejobs-svn``
 - ``jenkins-makejobs-hg``

All scripts accept the same command-line options and arguments and nearly the
same configuration files.

::

    Usage: jenkins-makejobs-* [-rvdtjnyoupUYOP] <config.yaml>

    General Options:
      -n dry run
      -v show version and exit
      -d debug config inheritance
      -t debug http requests

    Repository Options:
      -r <arg> repository url
      -y <arg> scm username
      -o <arg> scm password
      -Y scm username (read from stdin)
      -O scm password (read from stdin)

    Jenkins Options:
      -j <arg> jenkins url
      -u <arg> jenkins username
      -p <arg> jenkins password
      -U jenkins username (read from stdin)
      -P jenkins password (read from stdin)

Template Jobs
-------------

Autojobs creates jobs from template jobs. Subsequent changes to the
template jobs are propagated to all derived jobs (this behavior is
configurable). A template job can be any regular Jenkins job.
Depending on the SCM plugin you are using, you have to configure
certain fields:

**Git**:

::

    * Source Code Management:
      * Git:
        * Repository URL:   https://your.domain/your-project.git
        * Branch Specifier: master
        * Checkout/merge to local branch (under advanced): master

**Subversion**:

::

    * Source Code Management:
      * Subversion:
        * Repository URL:   https://your.domain/your-project
        * Local module directory (optional): .

**Mercurial**:

::

    * Source Code Management:
      * Mercurial:
        * Repository URL:   https://your.domain/your-project

One usage pattern is to have the job that builds your trunk/master
branch be your template job.


Configuration
-------------

Please refer to the annotated example configuration files for a
description of all options and their defaults:

.. toctree::
   examples

For a git-specific walkthrough, see the :doc:`use cases <usecases>`
page.


.. _pypi: http://pypi.python.org/pypi/jenkins-autojobs
.. _lxml:              http://lxml.de/



Case Study: Git
===============

Repository
----------

For the purposes of this tutorial we will create a git repository with
a few empty branches.

.. code-block:: bash

    $ git init /tmp/repo
    $ cd /tmp/repo
    $ git commit --allow-empty --allow-empty-message  -m ''
    $ git checkout -b develop
    $ git checkout -b feature/one
    $ git checkout -b feature/two
    $ git checkout -b release/one
    $ git show-ref | awk '{print $2}'
    refs/heads/master
    refs/heads/develop
    refs/heads/feature/one
    refs/heads/feature/two
    refs/heads/release/one


Template Jobs
-------------

We create two template jobs - one for all release branches (master,
release/one) and one for development branches (develop, feature/{one,two}).
You can configure them in any way you like, as long a *Branch Specifier* and
the *Checkout/merge to local branch* fields are not empty. In our case the two
template jobs will be imaginatively named 'release' and 'develop'.

::

    Job Name: release
    * Source Code Management:
      * Git:
        * Repository URL:   file:///tmp/repo
        * Branch Specifier: master
        * Checkout/merge to local branch (under advanced): master

    Job Name: develop
    * Source Code Management:
      * Git:
        * Repository URL:   file:///tmp/repo
        * Branch Specifier: develop
        * Checkout/merge to local branch (under advanced): develop


Initial Config
--------------

@Todo
