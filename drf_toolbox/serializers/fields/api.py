from __future__ import absolute_import, unicode_literals
from rest_framework import serializers
import collections


__all__ = ('APIEndpointField', 'APIEndpointsField')


class APIEndpointField(serializers.Field):
    """A Field subclass which checks the `get_absolute_url` method on the
    model object, and appropriately wraps the result.
    """
    def __init__(self):
        super(APIEndpointField, self).__init__()

        # Ensure that this field is always read only and not required.
        self.read_only = True
        self.requred = False

    def field_to_native(self, obj, field_name):
        """Return a string with the URL of the API endpoint of the
        given object.
        """
        # Get the base URL.
        url = self._get_base_url(obj)
        if not url:
            return None

        # Add the format if appropriate.
        url = self._apply_format(url)

        # Done; return the absolute URL.
        return url

    def _apply_format(self, url):
        """Apply the given format suffix to the end of the provided
        URL and return the result.
        """
        # Get the format in use.
        format = self.context.get('format', None)

        # Sanity check: If there is no format, do nothing.
        if not format:
            return url

        # Apply the format and return the result.
        return '%s.%s' % (url.rstrip('/'), format)

    def _get_base_url(self, obj):
        """Return the full base URL for this object."""

        request = self.context['request']

        # Sanity check: If the object model does not define a
        # `get_absolute_url` method, return None.
        if not hasattr(obj, 'get_absolute_url'):
            return None

        # Get the absolute URL of the object from the object's
        # model instance.
        url = obj.get_absolute_url()

        # Prepend the HTTP Host, if any.
        if request.get_host():
            url = '{scheme}://{host}{path}'.format(
                host=request.get_host(),
                path=url,
                scheme='https' if request.is_secure() else 'http',
            )

        # Return the final URL.
        return url


class APIEndpointsField(APIEndpointField):
    """An APIEndpointField subclass that returns back a dictionary of
    API endpoints, rather than a single string.
    """
    def __init__(self):
        super(APIEndpointsField, self).__init__()

        # By default we pay attention to child endpoints.
        self._honor_child_endpoints = True

    def initialize(self, parent, field_name):
        """Initialize this field.

        Maintain the superclass' initialization process, but also determine
        whether this is the base serializer for the viewset, by checking
        to see whether the context is in place yet.
        """
        return_value = super(APIEndpointsField, self).initialize(
            field_name=field_name,
            parent=parent,
        )

        # Sanity check: If we explicitly declare a serializer as a field,
        # it will be created before the context is put into place.
        #
        # This is important because `child_endpoints` is set in said context,
        # and will exist on all APIEndpointsField objects, when we actually
        # only want it on the base model being shown by the viewset.
        #
        # Since APIEndpointsField objects created on child serializers
        # won't have `child_endpoints` in their context yet, we can check
        # for the absence of `child_endpoints` at initialization time,
        # and that is a sufficient condition to ignore the `child_endpoints`
        # value that will be present on the context later.
        if 'child_endpoints' not in self.context:
            self._honor_child_endpoints = False

        # Return the superclass `initialize` method's return value.
        return return_value

    def field_to_native(self, obj, field_name):
        """Return a string with the URL of the API endpoint of the
        given object.
        """
        answer = collections.OrderedDict()

        # Get the base URL.
        url = self._get_base_url(obj)
        if not url:
            return {}

        # First, add the base URL as 'self'
        answer['self'] = self._apply_format(url)

        # If there are any child endpoints we should honor, add them
        # to the `answer` dictionary, in alphabetical order.
        if self._honor_child_endpoints:
            for ce in sorted(self.context.get('child_endpoints', [])):
                child_url = '%s/%s/' % (url.rstrip('/'), ce)
                answer[ce] = self._apply_format(child_url)

        # Done; return the final answer.
        return answer
