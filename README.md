## Welcome to DRF Toolbox

[![Build Status](https://travis-ci.org/feedmagnet/drf-toolbox.png)](https://travis-ci.org/feedmagnet/drf-toolbox) [![Coverage Status](https://coveralls.io/repos/feedmagnet/drf-toolbox/badge.png)](https://coveralls.io/r/feedmagnet/drf-toolbox)

**drf-toolbox** is a general set of enhancements for the excellent
[Django REST Framework][1], which enables fully-featured REST APIs written
on top of Django.

This project represents a collection of features to complement the basic
functionality provided by DRF, in particular:

  * Nesting models' API endpoints
  * Enhanced serialization, including:
      * The ability to show full, nested relationships, or a subset
        of fields
      * Optional use of UNIX timestamps in JSON models
      * Enhanced API endpoint serialization, using `get_absolute_url`.
  * Built-in support for fields provided by [django-pgfields][2]


### Installation & Dependencies

drf-toolbox can be installed using the usual means:

    pip install drf-toolbox

drf-toolbox requires Django 1.6 or higher, and Django REST Framework 2.3.10
or higher. If the django-pgfields are being used, 1.5.1 or higher is expected.


### License

New BSD.


### Documentation

Documentaiton is graciously hosted by [Read the Docs][3].

  [1]: http://www.django-rest-framework.org/
  [2]: http://django-pgfields.readthedocs.org/
  [3]: http://drf-toolbox.readthedocs.rog/
