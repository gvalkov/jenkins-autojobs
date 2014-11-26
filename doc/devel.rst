Testing
-------

The *jenkins-autojobs* test suite needs a running Jenkins instance,
pre-configured with the git, hg and svn plugins. To save you some of
the trouble of doing that, there is an `all-in-one script`_ that will
download `jenkins.war`_, bundle all necessary plugins and start a
local server on ``http://localhost:60888``.

.. code-block:: bash

    $ cd jenkins-autojobs/tests

    # start a jenkins server
    $ bin/start-jenkins.sh

    # if you want to gracefully shutdown the jenkins instance, either
    # kill the start-jenkins.sh process or send a 0 to localhost:60887
    # (60887 is the winstone control port)
    $ killall start-jenkins.sh
    $ echo 0 | nc 127.0.0.1 60887

.. code-block:: bash

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
   running any tests.

Todo
----

- The documentation still needs a lot of work.

.. _python-jenkins:    http://pypi.python.org/pypi/python-jenkins
.. _`all-in-one script`:  https://github.com/gvalkov/jenkins-autojobs/blob/master/tests/bin/start-jenkins.sh
.. _jenkins.war:       http://mirrors.jenkins-ci.org/war/latest/jenkins.war
