from __future__ import absolute_import, unicode_literals
from copy import copy
from django.utils.functional import cached_property
from drf_toolbox.compat import django_pgfields_installed, models
from drf_toolbox.serializers import ModelSerializer
from rest_framework import parsers, viewsets
from rest_framework.settings import api_settings


class ModelViewSet(viewsets.ModelViewSet):
    """ModelViewSet subclass that knows how to filter a queryset by
    unexpected keyword arguments.
    """
    @cached_property
    def parser_classes(self):
        answer = list(api_settings.DEFAULT_PARSER_CLASSES)

        # If django-pgfields is not installed, then we don't need
        # special behavior here; simply return what we have.
        if not django_pgfields_installed:
            return answer

        # Sanity check: Do we have any CompositeFields on this serializer?
        #
        # If we do, then the standard HTML form classes are not an option,
        # because we don't have a good way to represent the nested
        # relationships except through a format like JSON or YAML.
        fields = self.get_serializer_class().Meta.model._meta.fields
        for field in fields:
            # We're only interested in CompositeField subclasses;
            # ignore the rest.
            if not isinstance(field, models.CompositeField):
                continue

            # Some composite fields may define serializer fields that
            # do not need to suppress form parsing; if this is one of those
            # cases, do nothing.
            if hasattr(field, 'get_drf_serializer_field'):
                sf = field.get_drf_serializer_field()
                if not sf.suppress_form_parsing:
                    continue

            # Okay, we do actually need to suppress parsing using
            # form-urlencoded; do this now.
            problem_classes = (parsers.FormParser, parsers.MultiPartParser)
            for parser in reversed(copy(answer)):
                if issubclass(parser, problem_classes):
                    answer.pop(answer.index(parser))

        # Done; return the answer.
        return answer

    def get_queryset(self):
        """Return the appropriate queryset.  If we have unexpected keyword
        arguments from the URL, use those as keyword arguments to `.filter()`.
        """
        # Use the superclass implementation by default.
        qs = super(ModelViewSet, self).get_queryset()

        # Get the keyword arguments and values, if any.
        # 
        # Ignore the viewset's `lookup_field` kwarg if it's sent; this
        # corresponds to the exact object being asked for, and is handled
        # later in DRF's processing.
        filter_kwargs = copy(getattr(self, 'kwargs', {}))
        filter_kwargs.pop(getattr(self, 'lookup_field', 'pk'), None)
        filter_kwargs.pop('format', None)
        if filter_kwargs:
            return qs.filter(**filter_kwargs)

        # Return the superclass implementation as is.
        return qs

    def get_serializer(self, instance=None, data=None, files=None, many=False,
                             partial=False):
        """ Return the serializer instance that should be used for validating
        and deserializing input, and for serializing output.

        Cause any model fields that correspond to parent viewsets to be
        set to read only and populated appropriately.
        """
        # Perform the standard class and context retreival.
        serializer_class = self.get_serializer_class()
        context = self.get_serializer_context()

        # Resolve any fields present on the request itself.
        initial = {}
        for lookup_field, lookup_value in getattr(self, 'kwargs', {}).items():
            # Sanity check: Is this, in fact, a foreign key specified
            # in our URL?
            if not lookup_field.endswith('__pk'):
                continue

            # Get the field name.
            field_name = lookup_field.rstrip('__pk')

            # Sanity check: Is this a lookup traversing multiple levels?
            # If so, we don't need it.
            if '__' in field_name:
                continue

            # This should correspond to a field on the serializer;
            # mark it as read only and set its value in data.
            initial[field_name] = lookup_value

        # Sanity check: If we have a non-empty `initial` value, verify
        # that the serializer class understands how to accept it.
        if initial and not issubclass(serializer_class, ModelSerializer):
            raise TypeError(
                'The serializer class must be a subclass of '
                '`drf_toolbox.serializers.ModelSerializer` in order '
                'to be used with a nested viewset.'
            )

        # Now complete the superclass implementation.
        serializer = serializer_class(instance,
            data=data, files=files, initial=initial, many=many,
            partial=partial, context=context,
        )

        # Cause the fields identified above to be marked read only and
        # not required.
        for field_name in initial.keys():
            if field_name in serializer.fields:
                serializer.fields[field_name].read_only = True
                serializer.fields[field_name].required = False

        # Return the serializer.
        return serializer

    def get_serializer_context(self):
        answer = super(ModelViewSet, self).get_serializer_context()
        answer['child_endpoints'] = list(getattr(self, 'children', {}).keys())

        # Check for any special routes on this viewset, and identify
        # them as child endpoints.
        for method_name in dir(self):
            # Sanity check: Do not try to access `as_view`; it will
            # raise an exception as this is a ViewSet **instance**.
            #
            # Also, don't do anything on `parser_classes`, because we'll
            # end up in infinite-recursion.
            if method_name in ('as_view', 'parser_classes'):
                continue

            # Get the method, and add it to the endpoints list if it
            # has been routed.
            attr = getattr(self, method_name)
            if getattr(attr, 'bind_to_methods', None):
                answer['child_endpoints'].append(method_name)

        # Done; return the new context.
        return answer
