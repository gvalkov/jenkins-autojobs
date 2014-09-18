Installation
------------

The latest stable version of *jenkins-autojobs* is available on
PyPi_, while the development version can be installed directly from
github:

.. code-block:: bash

    $ pip install jenkins-autojobs  # latest stable version
    $ pip install git+git://github.com/gvalkov/jenkins-autojobs.git  # latest development version

Alternatively, *jenkins-autojobs* can be installed like any other Python package:

.. code-block:: bash

    $ git clone https://github.com/gvalkov/jenkins-autojobs.git
    $ cd  jenkins-autojobs
    $ git tag -l # List possible versiontags
    $ git reset --hard $versiontag
    $ python setup.py install

*Jenkins-autojobs* requires a version of lxml_ that supports XML
canonicalization (c14n). Setup will attempt to install one if it is
missing from your system or if you're in a virtualenv_ that does not
have access to the system's ``site-packages``. In that case, you have
to install the development headers for ``libxml`` and ``libxslt``.

On a Debian compatible OS:

.. code-block:: bash

    $ apt-get install libxml2-dev libxslt1-dev

On a Redhat compatible OS:

.. code-block:: bash

    $ yum install libxml2-devel libxslt-devel

.. _lxml:       http://lxml.de/
.. _PyPi:       http://pypi.python.org/pypi/jenkins-autojobs
.. _virtualenv: http://pypi.python.org/pypi/virtualenv/
