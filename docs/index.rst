Welcome to drf-toolbox
======================

This is drf-toolbox, a set of specialty classes that adds support
for enhanced functionality on top of `Django REST Framework`_.

DRF toolbox works with Django REST Framework and adds specialty classes
to provide the following functionality:

* Nested relationships for Foreign Keys
    * Nesting of URLs of parent-child relationships within URL routing.
    * Display of full parent or child relationships within renderers.
    * Support for more robust display of API endpoints.
* Support for fields provided by `django-pgfields`_.
* JSON rendering of ``datetime`` objects to Unix timestamps.


.. _Django REST Framework: http://djangorestframework.org/
.. _django-pgfields: http://django-pgfields.readthedocs.org/

Dependencies & Limitations
--------------------------

drf-toolbox depends on:

* Python 2.7+ or 3.3+ (Python 2.6 probably works, but is not explicitly
  tested against.)
* Django 1.6+
* Django REST Framework 2.3.10+
* dict.sorted 1.0.0+
* pytz 2013.9+
* six 1.4.1+

These dependencies are installed automatically when installing through pip.


Quick Start
-----------

In order to use drf-toolbox in a project:

* Installation
    * ``pip install drf-toolbox``
* Usage
    * Add DRF Toolbox' classes to your REST Framework settings, where
      appropriate.
    * Subclass DRF Toolbox' model serializer and model viewset.


Getting Help
------------

If you think you've found a bug in drf-toolbox itself, please post an
issue on the `Issue Tracker`_.

For usage help, you're free to e-mail the authors, who will provide help (on
a best effort basis) if possible.


License
-------

New BSD.


Index
-----

.. toctree::
    :maxdepth: 2

    nested
    pgfields
    json


.. _Issue Tracker: https://github.com/feedmagnet/drf-toolbox/issues
