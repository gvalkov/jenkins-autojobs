Installation
------------

The latest stable version of :mod:`jenkins-autojobs` is available on
PyPi_, while the development version can be installed directly from
github:

.. code-block:: console

    $ pip install jenkins-autojobs # latest stable version
    $ pip install git+git://github.com/gvalkov/jenkins-autojobs.git # latest development version

Alternatively, :mod:`jenkins-autojobs` can be installed like any other
:mod:`distutils`/:mod:`setuptools`/:mod:`packaging` package:

.. code-block:: console

    $ git clone git@github.com:gvalkov/jenkins-autojobs.git
    $ cd  jenkins-autojobs
    $ git reset --hard HEAD $versiontag
    $ python setup.py install

:mod:`jenkins-autojobs` requires a version of lxml_ that supports XML
canonicalization (c14n). Setup will attempt to install one if it is
missing from your system (or if you're in a virtualenv_ without access
to the system's ``site-packages`` dir). In that case, you would need to
install the development headers for ``libxml`` and ``libxslt``, which in
most cases can be done with:

.. code-block:: console

    $ apt-get install libxml2-dev libxslt1-dev
    # or
    $ yum install libxslt-devev libxml-devel


.. _lxml:       http://lxml.de/
.. _PyPi:       http://pypi.python.org/pypi/jenkins-autojobs
.. _virtualenv: http://pypi.python.org/pypi/virtualenv/
