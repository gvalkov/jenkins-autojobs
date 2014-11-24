Changelog
---------

0.14.2 (Nov 24, 2014)
^^^^^^^^^^^^^^^^^^^^^

- Fix reading of scm-username and scm-password from stdin (thanks `@yamikuronue`_).

- Fix user input on Python 3.

- Fix typo that was preveneting jenkins-autojobs from working on
  Python 2.6 (thanks `@aklemp`_).

0.14.1 (Nov 23, 2014)
^^^^^^^^^^^^^^^^^^^^^

- Ignore the 'All' view when adding jobs to views (thanks `@myz`_).

- View creation now respects the dryrun (-n) option (thanks `@aklemp`_).

- Fix reporting of view creation (thanks `@aklemp`_).

- Fix the httpdebug (-t) option on Python 3. The `httpdebug` option is
  now available in the config file.

0.14.0 (Oct 27, 2014)
^^^^^^^^^^^^^^^^^^^^^

- Learned the ability to add generated jobs to specific views.

- Fix compatiblity with newer version of the Jenkins Mercurial plugin (thanks `@ThomasMatern`_).

0.13.1 (May 29, 2014)
^^^^^^^^^^^^^^^^^^^^^

- Add the ``tag`` config option to the subversion script (thanks `@mrook`_).

0.13.0 (Apr 08, 2014)
^^^^^^^^^^^^^^^^^^^^^

- Add the ``tag`` config option.

- The ``cleanup`` option now accepts a tag name.

- The ``substitute`` option now has access to matched groups (thanks `@traviscosgrave`_).

- The ``substitute`` and ``namefmt`` options can now refer to named capture groups. For example:

  .. code-block:: yaml

      refs:
        - 'refs/heads/feature-(\d\d)-(?P<name>\w+)-(\d)':
            namefmt: 'wip-{name}-{3}'

  The above ref config will map the branch ``feature-random-10`` to
  job ``wip-random-10``.

0.12.0 (Mar 09, 2014)
^^^^^^^^^^^^^^^^^^^^^

- Fix a bug that made jenkins-autojobs remove all managed jobs if
  ``list_branches()`` failed with ``cleanup`` on (thanks `@sja`_).

- Use jenkins-webapi_ 0.2.0.

0.11.0 (Feb 04, 2014)
^^^^^^^^^^^^^^^^^^^^^

- Add the ``cleanup`` config option (thanks `@timmipetit`_).

  If set to ``true``, jenkins-autojobs will remove all jobs for which
  a branch no longer exists.

- Jenkins-autojobs now adds a ``createdByJenkinsAutojobs`` element to
  the ``config.xml`` of jobs that it creates.

0.10.0 (Jan 08, 2014)
^^^^^^^^^^^^^^^^^^^^^

- Add the ``sanitize`` config option (thanks `@xgouchet`_).

  You can now substitute characters or whole patterns with the
  ``sanitize`` option:

  .. code-block:: yaml

      sanitize:
        '@!?#&|\^_$%*': '_'    # replace any of '@!?#&|\^_$%*' with '_'
        're:colou?r': 'color'  # replace regex 'colou?r' with 'color'

  The default is ``'@!?#&|\^_$%*': '_'``, which is the list of
  characters that are not allowed in job names.

0.9.1 (Jan 08, 2014)
^^^^^^^^^^^^^^^^^^^^

- Command line flags ``-u|-p`` properly overwrite ``username`` and
  ``password`` config keys (thanks `@timmipetit`_).

0.9.0 (Nov 27, 2013)
^^^^^^^^^^^^^^^^^^^^

- Add support for Python 3.x.

- Add the 'python' option to the mercurial yaml config. This sets the
  Python executable that will be used to call mercurial. This is
  useful when the default Python in ``PATH`` is not Python 2.x.

- Use jenkins-webapi_ instead of python-jenkins_.

0.6.0 (Sep 05, 2012)
^^^^^^^^^^^^^^^^^^^^

- Add mercurial support.

0.5.0 (Aug 06, 2012)
^^^^^^^^^^^^^^^^^^^^

*Initial Release*.

.. _jenkins-webapi: https://pypi.python.org/pypi/jenkins-webapi
.. _python-jenkins: https://pypi.python.org/pypi/python-jenkins

.. _`@timmipetit`:     https://github.com/timmipetit
.. _`@xgouchet`:       https://github.com/xgouchet
.. _`@sja`:            https://github.com/sja
.. _`@traviscosgrave`: https://github.com/traviscosgrave
.. _`@mrook`:          https://github.com/mrook
.. _`@ThomasMatern`:   https://github.com/ThomasMatern
.. _`@aklemp`:         https://github.com/aklemp
.. _`@myz`:            https://github.com/myz
.. _`@yamikuronue`:    https://github.com/yamikuronue
