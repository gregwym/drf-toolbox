from __future__ import absolute_import, unicode_literals
from copy import copy
from django.core import exceptions
from django.db.models.fields import FieldDoesNotExist
from rest_framework import serializers
from rest_framework.compat import smart_text
from rest_framework.settings import api_settings


__all__ = ('RelatedField',)


class RelatedField(serializers.HyperlinkedRelatedField):
    """Related field class that returns both the ID and
    the API endpoint URL.
    """
    def __init__(self, seen_models, **kwargs):
        self._seen_models = set(seen_models)
        self._fields = kwargs.pop('fields', [])
        self._exclude = kwargs.pop('exclude', [])
        super(RelatedField, self).__init__(**kwargs)

    def from_native(self, value):
        """Return the appropriate model instance object based on the
        provided value.
        """
        params = {}
        defaults = {}

        # If the user sent a non-dictionary, then we assume we got the
        # ID of the foreign relation as a primative.  Convert this to a
        # dictionary.
        if not isinstance(value, dict):
            params['pk'] = value
        else:
            params = value

        # Remove any parameters that aren't unique values.
        # We are *only* able to use unique values to retrieve records
        # in this situation.
        rel_model = self.queryset.model
        for key in copy(params).keys():
            # If this is `pk`, it's known good; move on.
            if key == 'pk':
                continue

            # If this key is in any `unique_together` specification, then
            # keep it.
            if any([key in ut for ut in rel_model._meta.unique_together]):
                continue

            # If this key corresponds to a unique field, keep it.
            try:
                field = rel_model._meta.get_field_by_name(key)[0]
                if field.unique or field.primary_key:
                    continue
            except FieldDoesNotExist:
                # If this is a key in our serializer that simply
                # isn't a model field, that means it corresponds to the DRF
                # default output, and we can ignore it.
                serializer = self._get_serializer(rel_model())
                if key in serializer.fields:
                    params.pop(key)
                    continue

                # This is a field we totally don't recognize; complain.
                raise exceptions.ValidationError('Unknown field: `%s`.' % key)

            # Okay, this isn't a key we should have in our lookup;
            # it's superfluous.
            #
            # Store it in defaults so that it can be used to update
            # the object if necessary.
            defaults[key] = params.pop(key)

        # Sanity check: Are there any parameters left?
        # If no unique parameters were provided, we have no basis on which
        # to do a lookup.
        if not len(params):
            raise exceptions.ValidationError('No unique (or jointly-unique) '
                                             'parameters were provided.')

        # Perform the lookup.
        try:
            return self.queryset.get(**params)
        except exceptions.ObjectDoesNotExist:
            error_msg = 'Object does not exist with: %s.' % smart_text(value)
        except exceptions.MultipleObjectsReturned:
            error_msg = 'Multiple objects returned for: {0}.'.format(
                smart_text(value),
            )
        except (TypeError, ValueError):
            error_msg = 'Type mismatch.'
        raise exceptions.ValidationError(error_msg)

    def label_from_instance(self, obj):
        return smart_text(obj)

    def prepare_value(self, obj):
        return obj.pk

    def to_native(self, obj):
        """Return a dictionary including both the ID and the API's
        endpoint URL.
        """
        # Sanity check: Does this object have a primary key yet?
        # If not, there's nothing we can do
        if not getattr(obj, 'pk', None):
            return None

        # Return back a dictionary of fields.
        return self._get_serializer(obj).data

    def _create_serializer_class(self, model_class):
        """Create a serializer class for this related field,
        and save it on this class instance.

        Return True if a new class was created, False otherwise.
        """
        # Save a serializer for the related model on this object
        # if and only if there isn't one already.
        if not hasattr(self, '_serializer_class'):
            class Serializer(api_settings.DEFAULT_MODEL_SERIALIZER_CLASS):
                class Meta:
                    model = model_class
                    fields = self._fields
                    exclude = self._exclude
            self._serializer_class = Serializer
            return True

        return False

    def _get_serializer(self, obj):
        """Return a serializer object corresponding to this related
        model class.
        """
        # Ensure that we have a serializer class created.
        self._create_serializer_class(model_class=obj.__class__)

        # Remove any child endpoints from the context; these are child
        # endpoints of the base serializer, not its children.
        context = copy(self.context)
        context.pop('child_endpoints', None)

        # Return an instance of the serializer class.
        return self._serializer_class(obj, seen_models=self._seen_models,
                                           context=context)
