.. image:: img/autojobs-logo-expanded.png
   :align: center


Introduction
============

Jenkins-autojobs is a set of scripts that automatically create Jenkins
jobs from template jobs and the branches in an SCM repository.
Jenkins-autojobs supports Git_, Mercurial_ and Subversion_.

A routine run goes through the following steps:

- Read settings from a configuration file.
- List branches or refs from SCM.
- Creates or updates jobs as configured.

In its most basic form, the configuration file specifies:

- How to access Jenkins and the SCM repository.
- Which branches to process and which to ignore.
- Which template job to use for which branches.
- How new jobs should be named.

Autojobs can also;

- Add newly created jobs to Jenkins views.
- Cleanup jobs for which a branch no longer exists.
- Perform text substitutions on all text elements of a job's ``config.xml``.
- Update jobs when their template job is updated.
- Set the enabled/disabled state of new jobs. A new job can inherit
  the state of its template job, but an updated job can keep its most
  recent state.

Please refer to the :doc:`tutorial <tutorial>` and the :doc:`example
output <exampleoutput>` to get started. You may also have a look at
the annotated :ref:`git <gityamlconfig>`, :ref:`svn <svnyamlconfig>`
and :ref:`hg <hgyamlconfig>` config files.

**Notice**: The documentation is in the process of being completely
rewritten. Things may seem incomplete and out of place.


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


Changes
-------

.. toctree::
   changelog

.. toctree::
   :hidden:

   tutorial
   usecases
   exampleoutput


Development
-----------

.. toctree::
   devel


Similar Projects
----------------

* jenkins-build-per-branch_
* jenkins-job-builder_


License
-------

Jenkins-autojobs is released under the terms of the `Revised BSD
License`_. All figures are derived from the Jenkins logo and are
released under the `CC BY-SA 3.0`_ license.


.. _pypi: http://pypi.python.org/pypi/jenkins-autojobs
.. _github:            https://github.com/gvalkov/jenkins-autojobs
.. _`Revised BSD License`: https://raw.github.com/gvalkov/jenkins-autojobs/master/LICENSE
.. _`Sidebar-Link`:    https://wiki.jenkins-ci.org/display/JENKINS/Sidebar-Link+Plugin
.. _python-jenkins:    http://pypi.python.org/pypi/python-jenkins
.. _jenkins-build-per-branch: http://entagen.github.com/jenkins-build-per-branch/
.. _jenkins-job-builder: https://pypi.python.org/pypi/jenkins-job-builder/
.. _git:               https://wiki.jenkins-ci.org/display/JENKINS/Git+Plugin
.. _subversion:        https://wiki.jenkins-ci.org/display/JENKINS/Subversion+Plugin
.. _mercurial:         https://wiki.jenkins-ci.org/display/JENKINS/Mercurial+Plugin
.. _`CC BY-SA 3.0`:    http://creativecommons.org/licenses/by-sa/3.0/
