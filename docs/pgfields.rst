Fields from django-pgfields
===========================

DRF Toolbox provides out of the box support for fields from `django-pgfields`_
if and only if django-pgfields is installed. No setup is required to get
this functionality; it is auto-enabled if django-pgfields is present, and
dormant if django-pgfields is absent.

.. note::

    While the other three fields come with standard form elements,
    ``CompositeField`` classes do not have any straightforward form
    rendering.

    As a result, when a ``CompositeField`` is used, the form data parser
    is *removed* from the viewset unless it was manually specified.

.. _django-pgfields: http://django-pgfields.readthedocs.org/

