Changelog
---------

0.11.0 (Feb 04, 2014)
^^^^^^^^^^^^^^^^^^^^

- Add the ``cleanup`` config option (thanks `@timmipetit`_).

  If set to ``true``, jenkins-autojobs will remove all jobs for which
  a branch no longer exists.

- Jenkins-autojobs now adds a ``createdByJenkinsAutojobs`` element to
  the config.xml of jobs that it has created.

0.10.0 (Jan 08, 2014)
^^^^^^^^^^^^^^^^^^^^

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

.. _`@timmipetit`:  https://github.com/timmipetit
.. _`@xgouchet`:    https://github.com/xgouchet
