Mercurial Setup
===============

Jenkins
-------

The ``jenkins-makejobs-hg`` script works with template jobs configured
with the `Mercurial SCM`_ plugin. No special configuration other than
enabling the plugin and setting a repository location is needed. The
script will take care of setting the branch (the branch that the job
will checkout) for every new job created from the template job.

.. _hgyamlconfig:


Config file
-----------

.. literalinclude:: hg-config.yaml
   :language: yaml
.. :linenos:

:download:`Download hg-config.yaml <hg-config.yaml>`


``repo``
********

Url to the mercurial repository.


``namefmt``
***********

Template string to use for job names.

Given a branch ``branches/svn-bisect``, the following table
maps the available placeholders to their respectful values:

=====================     =======================================
 placeholder                   value
=====================     =======================================
 ``{branch}``              ``branches-svn-bisect``
 ``{branch-orig}``         ``branches/svn-bisect``
 ``{0}``                   ``svn``
 ``{1}``                   ``bisect``
=====================     =======================================

Assumes that the following config:

.. code-block:: yaml

    refs:
      - 'branches/(.*)-(.*)'
        namesep: '-'

Placeholders such as ``{0} {1} {2}`` evaluate to the
backreferences (``\1 \2 \3``) of the matching regular expression (see refs_).

.. note::

   Using ``branch-orig`` would most likely result in an error, since
   some of the characters allowed in branch names cannot be used for
   job names.


``refs``
********

A list of regular expressions that specify the branches to process:

.. code-block:: yaml

    refs:
      - 'feature-.*'
      - 'bug-.*'

Global settings can be overwritten on a per-ref basis:

.. code-block:: yaml

    namefmt:  'job-{branch}'
    template: 'template-one'

    refs:
      - 'feature-.*'
      - 'alpha-(.*)':
          namefmt:  'bug-{1}'
          template: 'bug-template'

=============================  ======================  ========================
ref                            new job name            template
=============================  ======================  ========================
``alpha-1``                     ``bug-alpha-1``         ``bug-template``
``branches/feature-1``          ``job-feature-1``       ``template-one``
=============================  ======================  ========================

Note that the namefmt_ setting can use backreferences from the regular
expressions through the ``{n}`` placeholder:

.. code-block:: yaml

    refs:
      - 'experimental/(.*)/(.*)'

Given a branch ``experimental/john/feature-one`` the placeholders will
be expanded as:

=============================  ======================
placeholder                    value
=============================  ======================
``{0}``                        ``john``
``{1}``                        ``feature-one``
=============================  ======================

Defaults to:

.. code-block:: yaml

    refs:
      - '.*'


``substitute``
**************

See :ref:`href-substitute`

.. _`Mercurial SCM`:   https://wiki.jenkins-ci.org/display/JENKINS/Mercurial+Plugin
