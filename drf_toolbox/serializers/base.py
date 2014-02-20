from __future__ import absolute_import, unicode_literals
from copy import copy
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import NoReverseMatch
from django.db.models.fields import FieldDoesNotExist
from drf_toolbox.compat import models, django_pgfields_installed
from drf_toolbox.serializers.fields import api, postgres, related
from importlib import import_module
from rest_framework import serializers
from rest_framework.compat import smart_text
from rest_framework.settings import api_settings
import collections
import six


__all__ = ('BaseModelSerializer', 'ModelSerializer')


API_ENDPOINT_KEY_SINGULAR = 'api_endpoint'
API_ENDPOINT_KEY_PLURAL = 'api_endpoints'


class BaseModelSerializer(serializers.ModelSerializer):
    """A model serializer that is the starting point for any
    extentions consistently needed in the DRF Toolbox API.
    """
    def get_field(self, model_field):
        """Return the appropriate Django REST Framework field for this
        model field.
        """
        # If django-pgfields is not installed, then just take
        # the superclass implementation.
        if not django_pgfields_installed:
            return super(BaseModelSerializer, self).get_field(model_field)

        # If this is an ArrayField, we need to send the `of` subfield
        # as well as the field itself.
        if isinstance(model_field, models.ArrayField):
            of_field = self.get_field(model_field.of)
            return postgres.ArrayField(of_field,
                default=[],
                help_text=model_field.help_text,
                label=model_field.verbose_name,
                read_only=not model_field.editable,
                required=not model_field.blank,
            )

        # If this field is a CompositeField subclass, we can just use
        # an intelligent CompositeField serialization class to handle it.
        if isinstance(model_field, models.CompositeField):
            # Composite fields may define their own serializers.
            # If this one does, return it.
            if hasattr(model_field, 'get_drf_serializer_field'):
                return model_field.get_drf_serializer_field()

            # Create and return a generic composite field serializer.
            subfields = {}
            for name, model_subfield in model_field._meta.fields:
                subfields[name] = self.get_field(model_subfield)
            return postgres.CompositeField(
                default=model_field.instance_class(),
                fields=subfields,
                help_text=model_field.help_text,
                label=model_field.verbose_name,
                instance_class=model_field.instance_class,
                read_only=not model_field.editable,
                required=not model_field.blank,
            )

        # If this field is a JSONField, then use the simple JSONField
        # serialization class.
        if isinstance(model_field, models.JSONField):
            return postgres.JSONField(
                default={},
                help_text=model_field.help_text,
                label=model_field.verbose_name,
                read_only=not model_field.editable,
                required=not model_field.blank,
            )

        # If this field is a UUIDField, then use the UUIDField serialization
        # class also.
        if isinstance(model_field, models.UUIDField):
            if model_field._auto_add:
                return postgres.UUIDField(read_only=True, required=False)
            return postgres.UUIDField(
                default=model_field.default,
                help_text=model_field.help_text,
                label=model_field.verbose_name,
                read_only=not model_field.editable,
                required=not model_field.blank,
            )

        # Okay, this isn't a special field; run the superclass implementation.
        return super(BaseModelSerializer, self).get_field(model_field)


class ModelSerializer(BaseModelSerializer):
    """A model serializer which prints both endpoints and
    IDs for each record.
    """
    _default_view_name = '%(model_name)s-detail'
    _options_class = serializers.HyperlinkedModelSerializerOptions

    class Meta:
        depth = 1

    def __init__(self, obj=None, seen_models=(), initial=None, **kwargs):
        self._seen_models = set(seen_models)
        self._initial = initial or {}
        self._rel_fields = {}
        super(ModelSerializer, self).__init__(obj, **kwargs)

    def get_default_fields(self):
        """Return the default fields for this serializer, as a
        dictionary.
        """
        # If we received the `fields` or `exclude` options as dictionaries,
        # parse them out into the format that DRF expects.
        #
        # We can then address our related fields lists by sending them
        # to the appropriate related fields.
        for option in ('fields', 'exclude'):
            opt_value = getattr(self.opts, option, ())
            if isinstance(opt_value, dict):
                setattr(self.opts, option, opt_value.get('self', ()))
                self._rel_fields[option] = opt_value

        # Perform the superclass behavior.
        fields = super(ModelSerializer, self).get_default_fields()

        # Expunge created, modified, and password if they are present.
        # These fields should only be sent if specifically requested.
        for field_name in ('created', 'modified', 'password'):
            if field_name not in self.opts.fields:
                fields.pop(field_name, None)

        # Expunge any fields that are related fields to models
        # that we have already seen.
        for field_name, field in fields.items():
            if (isinstance(field, related.RelatedField) and
                            field.queryset.model in self._seen_models):
                fields.pop(field_name, None)

        # Ensure that we have a view name.
        if not self.opts.view_name:
            self.opts.view_name = self._get_default_view_name()

        # Use an OrderedDict to cause our keys to be in mostly-alpha order.
        answer = collections.OrderedDict()

        # Exception: We always want the primary key to come first, as it is
        # the identifier for the object.
        pk_field_name = self.opts.model._meta.pk.name
        answer[pk_field_name] = fields[pk_field_name]

        # Add the `api_endpoints` field, which will give us the
        # hyperlink to the given item.
        # 
        # Do it at this point, which will cause the API endpoint field
        # to be shown second.
        viewset = self.context.get('view', None)
        if (hasattr(self.opts.model, 'get_absolute_url')):
            if viewset and self._viewset_uses_me(viewset):
                answer.setdefault(API_ENDPOINT_KEY_PLURAL,
                                  api.APIEndpointsField())
            else:
                answer.setdefault(API_ENDPOINT_KEY_SINGULAR,
                                  api.APIEndpointField())

        # Now add all other fields, in alphabetical order.
        for key in sorted(fields.keys()):
            # Sanity check: Don't try to add the primary key field twice.
            if key == pk_field_name:
                continue
            answer[key] = fields[key]

        # Sanity check: If the "api_endpoint" or "api_endpoints" field
        # is explicitly included or excluded, but we got the other, be
        # gracious and just change it under the hood.
        #
        # This gets around a slew of problems where it becomes extraordinarily
        # difficult to initialize serializers outside of the entire
        # request setup.
        for option in ('fields', 'exclude'):
            opt_value = getattr(self.opts, option, [])
            original_class = type(opt_value)
            if (API_ENDPOINT_KEY_SINGULAR in opt_value and
                                    API_ENDPOINT_KEY_PLURAL in answer):
                opt_value = list(opt_value)
                index = opt_value.index(API_ENDPOINT_KEY_SINGULAR)
                opt_value[index] = API_ENDPOINT_KEY_PLURAL
            if (API_ENDPOINT_KEY_PLURAL in opt_value and
                                    API_ENDPOINT_KEY_SINGULAR in answer):
                opt_value = list(opt_value)
                index = opt_value.index(API_ENDPOINT_KEY_PLURAL)
                opt_value[index] = API_ENDPOINT_KEY_SINGULAR
            setattr(self.opts, option, original_class(opt_value))

        # Done; return the final answer.
        return answer

    def get_related_field(self, model_field, related_model, to_many):
        """Returns a representation of the related field,
        to be shown in a nested fashion.
        """
        # Set default keyword arguments.
        kwargs = {
            'many': to_many,
            'queryset': related_model._default_manager,
            'view_name': self._get_default_view_name(related_model),
        }

        # If we have set filter or exclude lists for this related field,
        # add them to the kwargs.
        #
        # This bit of code is expecting a `self._rel_fields` to be a
        # dictionary that looks kind of like this:
        #   {'fields': 'child_model': ('id', 'api_endpoint', 'foo', 'bar'),
        #    'exclude': 'other_model': ('password',)}
        #
        # Essentially what will happen is that it will check for this
        # related model's key within both the fields and exclude sub-dicts,
        # and if they are found, they are added to keyword arguments
        # used to init the RelatedField.
        for key, field_lists in self._rel_fields.items():
            if model_field.name in field_lists:
                kwargs[key] = field_lists[model_field.name]

        # If there is a model field (e.g. this is not a reverse relationship),
        # determine whether or not the field is required.
        if model_field:
            kwargs['required'] = not (model_field.null or model_field.blank)

        # Create a new set object that includes all seen models,
        # as well as the current model, to send to the related field.
        seen_models = self._seen_models.union({ self.opts.model })

        # Instantiate and return our field.
        rel_field = related.RelatedField(seen_models=seen_models, **kwargs)
        rel_field.parent_serializer = self
        return rel_field

    def save_object(self, obj, **kwargs):
        """Save the provided model instance.

        If initial data was provided when this serializer was instantiated,
        set the appropriate fields on the model instance before saving.
        """
        for key, value in self._initial.items():
            setattr(obj, key, self._find_field(key).from_native(value))
        return super(ModelSerializer, self).save_object(obj, **kwargs)

    def _find_field(self, key):
        """Return the field with the given field name.
        If the field does not exist, raise KeyError.

        This method also returns a field that exists, but is no longer on
        the serializer (e.g. a default field that is excluded).
        """
        return self.fields.get(key, self.get_default_fields()[key])

    def _get_default_view_name(self, model=None):
        """Return the name to assign in the URL configuration if none
        is provided in the `Meta` inner class.
        """
        # If no model is provided, assume we're dealing with
        # the model on this serializer.
        if not model:
            model = self.opts.model

        # Determine from the models `Meta` inner class what
        # an appropriate view name is.
        model_meta = model._meta
        format_kwargs = {
            'app_label': model_meta.app_label,
            'model_name': model_meta.object_name.lower()
        }
        return self._default_view_name % format_kwargs

    def _viewset_uses_me(self, viewset):
        """Given a viewset, return True if we believe that the viewset uses
        this serializer class, False otherwise.
        """
        # Get the serializer class that this viewset uses.
        sc = viewset.get_serializer_class()

        # If this serializer class is the same class as this instance,
        # then it's definitely a match.
        if sc == type(self):
            return True

        # Irritating case: If this class uses the default serializer, *and*
        # the viewset does also, then this is a match.
        if (type(self).__name__ == 'DefaultSerializer' and 
                    isinstance(self, ModelSerializer) and
                    viewset.model == self.opts.model):
            return True

        # It's not a match.
        return False
