Development
===========

Testing
-------

The :mod:`jenkins-autojobs` test suite needs a running Jenkins
instance, pre-configured with the scm plugins that the scripts
support. To save you some of the trouble of doing that, there is an
all-in-one script that will download `jenkins.war`_, bundle all
necessary plugins and start a local server (see
`start-jenkins.sh`_). The test suite and the helper script default to
a Jenkins CI server listening on ``localhost:60888``.

.. code-block:: console

    $ cd jenkins-autojobs/tests

    # start a jenkins server
    $ bin/start-jenkins.sh

    # if you want to gracefully shutdown the jenkins instance, either
    # kill the start-jenkins.sh process or send a 0 to localhost:60887
    # (60887 is the winstone control port)
    $ killall start-jenkins.sh
    $ echo 0 | nc 127.0.0.1 60887

.. code-block:: console

    $ cd jenkins-autojobs

    # make sure that the jenkins_autojobs package is available on
    # sys.path (python setup.py develop in a virtualenv)

    # run all tests
    $ py.test tests

    # run only git tests
    $ py.test tests/test_git.py

    # run all tests for all supported versions of python
    $ tox

.. warning::

   The test suite **removes all jobs** on the Jenkins server prior to
   running the tests.

Todo
----

* Support more scm plugins (starting with mercurial, as I'm already
  advertising it in the documentation).

* Clean up the code. Initially these were all seperate scripts that
  didn't reuse any code at all. Merging them made things messy.

* Add Jenkins/SCM authentication tests.

* Handle deleted branches that have been fully merged (this just
  hasn't been a priority for me).

* Add Python 3 support. The source code itself should work on python
  2.7 and >=3.0, but the stable version of python-jenkins_ is holding
  me back. There are plenty of python bindings for the jenkins web
  api, but I'm a little dissatisfied with all of them and have been
  thinking of writing my own.


.. _python-jenkins:    http://pypi.python.org/pypi/python-jenkins
.. _start-jenkins.sh:  https://github.com/gvalkov/jenkins-autojobs/blob/master/tests/bin/start-jenkins.sh
.. _jenkins.war:       http://mirrors.jenkins-ci.org/war/latest/jenkins.war
