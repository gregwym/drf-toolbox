from __future__ import absolute_import, unicode_literals
from drf_toolbox.compat import django_pgfields_installed
from drf_toolbox.serializers.widgets import JSONWidget
from rest_framework import serializers
import six
import uuid


if django_pgfields_installed:
    __all__ = ('ArrayField', 'CompositeField', 'JSONField', 'UUIDField')
    

    class ArrayField(serializers.WritableField):
        """A REST Framework serialization field for handling arrays,
        serializing into Python lists.
        """
        type_label = 'list'

        def __init__(self, of, **kwargs):
            self.of = of
            super(ArrayField, self).__init__(**kwargs)

        def from_native(self, value):
            """Iterate over each item in the value, run it through the
            field's `from_native` method, and return the result.
            """
            return [self.of.from_native(i) for i in value]

        def to_native(self, value):
            """Iterate over each item in the value, run it through the
            field's `to_native` method, and return the result.
            """
            return [self.of.to_native(i) for i in value]


    class JSONField(serializers.WritableField):
        """A REST Framework serialization field for handling JSON fields,
        serializing them into an appropriate Python object.
        """
        type_label = 'object'
        widget = JSONWidget

        def from_native(self, value):
            return value

        def to_native(self, value):
            return value


    class CompositeField(serializers.WritableField):
        """A REST Framework serialization field for handling composite fields,
        serializing them into a Python dictionary and back.
        """
        type_label = 'dict'

        def __init__(self, fields, instance_class, **kwargs):
            self.fields = fields
            self.instance_class = instance_class
            super(CompositeField, self).__init__(**kwargs)

        def from_native(self, value):
            """Convert the dictionary into the appropriate composite instance
            class. Recursively run `from_native` on each value.
            """
            kwargs = {}
            for name, subval in value.items():
                subfield = self.fields[name]
                subfield.field_from_native(value, {}, name, kwargs)
            return self.instance_class(**kwargs)

        def to_native(self, value):
            """Iterate over each of the sub-fields in the CompositeField and
            transform them appropriately.
            """
            answer = {}
            for name, subfield in self.fields.items():
                answer[name] = subfield.field_to_native(value, name)
            return answer


    class UUIDField(serializers.CharField):
        """A REST Framework serialization field for handling UUID fields,
        serializing them into a string and back.
        """
        type_label = 'uuid'

        def from_native(self, value):
            return uuid.UUID(value)

        def to_native(self, value):
            return six.text_type(value)
else:
    __all__ = ()
