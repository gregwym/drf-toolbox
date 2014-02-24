from __future__ import absolute_import, unicode_literals
from collections import namedtuple
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models.fields import FieldDoesNotExist
from django.test.client import RequestFactory
from drf_toolbox.compat import django_pgfields_installed, models
from drf_toolbox.serializers import (fields, BaseModelSerializer,
                                     ModelSerializer, RelatedField)
from drf_toolbox.serializers.fields import api
from drf_toolbox import viewsets
from rest_framework import serializers
from rest_framework.relations import HyperlinkedIdentityField
from tests import models as test_models, serializers as test_serializers
from tests.compat import mock
import unittest
import six
import uuid


NO_DJANGOPG = 'django-pgfields is not installed.'


class SerializerSuite(unittest.TestCase):
    """Suite of test cases around custom serializers, ensuring that
    they provide expected output.
    """
    def test_api_endpoints_field_autocreated(self):
        """Establish that the `api_endpoints` key is auto-created on
        a serializer that doesn't explicitly define the field.
        """
        # Create a bogus viewset class, so the serializer can be
        # given context that is aware of it.
        class ViewSet(viewsets.ModelViewSet):
            model = test_models.NormalModel
            serializer_class = test_serializers.NormalSerializer

        # Create the serializer
        s = test_serializers.NormalSerializer()
        s.context = {
            'request': RequestFactory().get('/foo/bar/'),
            'view': ViewSet(),
        }

        # Ensure that the expected api.APIEndpointsField is present.
        df = s.get_default_fields()
        self.assertIn('api_endpoints', df)
        self.assertIsInstance(df['api_endpoints'], api.APIEndpointsField)

    def test_api_endpoints_field_default_serializer(self):
        """Establish that the the `api_endpoints` key is created for a
        default serializer.
        """
        # Create a bogus viewset class, so the serializer can be
        # given context that is aware of it.
        class ViewSet(viewsets.ModelViewSet):
            model = test_models.NormalModel

        # Create the serializer.
        s = ViewSet().get_serializer_class()()
        s.context = {
            'request': RequestFactory().get('/foo/bar/'),
            'view': ViewSet(),
        }

        # Ensure that the expected api.APIEndpointField is present.
        df = s.get_default_fields()
        self.assertIn('api_endpoints', df)
        self.assertIsInstance(df['api_endpoints'], api.APIEndpointsField)

    def test_api_endpoint_field_default_serializer(self):
        """Establish that the the `api_endpoint` key is created in a case
        where we cannot match to the viewset, and we're still using a
        specific serializer.
        """
        # Create a bogus viewset class, so the serializer can be
        # given context that is aware of it.
        class Viewset(viewsets.ModelViewSet):
            model = test_models.NormalModel

        # Create the serializer.
        s = test_serializers.NormalSerializer()
        s.context = {
            'request': RequestFactory().get('/foo/bar/'),
            'view': Viewset(),
        }

        # Ensure that the expected api.APIEndpointField is present.
        df = s.get_default_fields()
        self.assertIn('api_endpoint', df)
        self.assertIsInstance(df['api_endpoint'], api.APIEndpointField)

    def test_api_endpoint_key_existing(self):
        """Test that if a set of fields is provided with an `api_endpoints`
        field, that we don't barrel over it.
        """
        # Ensure I get what I expect from `get_default_fields`.
        s = test_serializers.ExplicitAPIEndpointsSerializer()
        fields = s.get_default_fields()
        self.assertEqual(len(fields), 3)
        self.assertIsInstance(fields['api_endpoints'],
                              serializers.IntegerField)

    def test_api_endpoints_autocovert_plural_to_singular(self):
        """Establish that explicitly specifying `api_endpoint` or
        `api_endpoints` will graciously switch between them when necessary.
        """
        # Create a serializer to use for this test.
        class Serializer(test_serializers.NormalSerializer):
            class Meta:
                model = test_serializers.NormalSerializer.Meta.model
                fields = ('id', 'api_endpoints')

        # Establish that a serializer instance with no context will
        # have an api_endpoint field.
        s = Serializer()
        self.assertIn('api_endpoint', s.opts.fields)
        self.assertNotIn('api_endpoints', s.opts.fields)

    def test_api_endpoints_autocovert_singular_to_plural(self):
        """Establish that explicitly specifying `api_endpoint` or
        `api_endpoints` will graciously switch between them when necessary.
        """
        # Create a serializer to use for this test.
        class Serializer(test_serializers.NormalSerializer):
            class Meta:
                model = test_serializers.NormalSerializer.Meta.model
                fields = ('id', 'api_endpoint')

        # Establish that a serializer instance with no context will
        # have an api_endpoint field.
        with mock.patch.object(ModelSerializer, '_viewset_uses_me') as vum:
            vum.return_value = True
            s = Serializer(context={'view': object(),})
        self.assertIn('api_endpoints', s.opts.fields)
        self.assertNotIn('api_endpoint', s.opts.fields)

    def test_direct_relationship(self):
        """Test that a direct relationship retrieval works
        as expected.
        """
        # Get the related field from a direct relationship.
        s = test_serializers.ChildSerializer()
        rel_field = s.get_related_field(
            model_field=test_models.ChildModel._meta.\
                        get_field_by_name('normal')[0], 
            related_model=test_models.NormalModel,
            to_many=False,
        )
        self.assertIsInstance(rel_field, RelatedField)

        # Verify the label.
        self.assertEqual(
            rel_field.label_from_instance(test_models.NormalModel()),
            'NormalModel object',
        )

        # Verify the value.
        self.assertFalse(rel_field.prepare_value(test_models.NormalModel()))

    def test_direct_relationship_with_explicit_fields(self):
        """Test that a direct relationship retreival works as expected,
        and that our explicit field list chains down to the related field.
        """
        # Create our serializer.
        s = test_serializers.ChildSerializerII()
        rel_field = s.get_related_field(
            model_field=test_models.ChildModel._meta.\
                        get_field_by_name('normal')[0], 
            related_model=test_models.NormalModel,
            to_many=False,
        )
        self.assertIsInstance(rel_field, RelatedField)
        rel_field.context = {'request': RequestFactory().get('/foo/bar/')}

        # Get the serializer class.
        s = rel_field._get_serializer(test_models.NormalModel(bacon=42))
        self.assertEqual([i for i in s.get_fields().keys()], ['id', 'bacon'])

    def test_reverse_relationship(self):
        """Test that a reverse relationship retrieval works as
        expected.
        """
        # Instantiate my normal serializer and run a reverse
        # relationship against the fake child model.
        s = test_serializers.NormalSerializer()
        rel_field = s.get_related_field(None, test_models.ChildModel, False)
        self.assertIsInstance(rel_field, RelatedField)

    def test_related_field_with_no_pk(self):
        """Test that a related field receiving a model object
        with no primary key returns None.
        """
        rel_field = RelatedField(())
        answer = rel_field.to_native(test_models.ChildModel())
        self.assertEqual(answer, None)

    def test_related_field_with_pk(self):
        """Test that a related field receiving a model object
        with a primary key returns None.
        """
        # Create a fake request.
        factory = RequestFactory()
        request = factory.get('/foo/')

        # Get the appropriate related field.
        fake_pk = uuid.uuid4()
        nm = test_models.NormalModel(id=42)
        cm = test_models.ChildModel(normal=nm)
        cs = test_serializers.ChildSerializer(context={'request': request})
        rel_field = cs.get_related_field(
            model_field=test_models.ChildModel._meta.\
                        get_field_by_name('normal')[0], 
            related_model=test_models.NormalModel,
            to_many=False,
        )
        rel_field.context = { 'request': request }

        # Get the final answer.
        answer = rel_field.to_native(nm)
        self.assertEqual({
            'api_endpoint': 'http://testserver/normal/%d/' % nm.id,
            'id': 42,
            'bacon': None,
            'bar': None,
            'baz': None,
            'foo': None,
        }, answer)

    def test_reverse_related_field_serializer(self):
        """Establish that a related field can be specified on a serializer
        without incident.
        """
        # Create a bogus request object.
        factory = RequestFactory()
        request = factory.get('/foo/')

        # Create a serializer that would otherwise show itself
        # at a related level.
        rs = test_serializers.ReverseSerializer()

        # Create an instance.
        nm = test_models.NormalModel(bar=1, baz=2, bacon=3)
        rm = test_models.RelatedModel(id=42, baz=1, normal=nm)

        # Get the fields from the serializer and determine that we get
        # what we expect.
        fields_dict = rs.get_default_fields()
        self.assertEqual(
            [i for i in fields_dict.keys()],
            [
                'id', 'api_endpoint', 'bacon', 'bar',
                'baz', 'foo', 'related_model',
            ],
        )

        # Pull out the related field.
        rel_field = fields_dict['related_model']
        rel_field.context = {'request': request}

        # Convert our related field to native, and establish that it does not
        # have a normal model.
        native = rel_field.to_native(rm)
        self.assertEqual({'id': 42, 'baz': 1}, native)

    def test_create_rel_serializer_class(self):
        """Establish that the `RelatedField._create_serializer_class`
        method works as expected.
        """
        RelatedModel = test_models.RelatedModel

        # Create a bogus request object.
        factory = RequestFactory()
        request = factory.get('/foo/')

        # Create a serializer that would otherwise show itself
        # at a related level.
        rs = test_serializers.ReverseSerializer()

        # Create an instance.
        nm = test_models.NormalModel(bar=1, baz=2, bacon=3)
        rm = RelatedModel(id=42, baz=1, normal=nm)

        # Get the fields from the serializer and determine that we get
        # what we expect.
        fields_dict = rs.fields
        self.assertEqual(
            set([i for i in fields_dict.keys()]),
            {'bacon', 'bar', 'baz', 'related_model'},
        )

        # Pull out the related field.
        rel_field = fields_dict['related_model']
        rel_field.context = {'request': request}

        # Establish that there is no serializer class on the related
        # field yet.
        self.assertFalse(hasattr(rel_field, '_serializer_class'))

        # Create a serializer class.
        ret_val = rel_field._create_serializer_class(RelatedModel)
        self.assertTrue(ret_val)
        self.assertTrue(hasattr(rel_field, '_serializer_class'))
        sc = rel_field._serializer_class

        # Establish that a followup call is a no-op.
        ret_val = rel_field._create_serializer_class(RelatedModel)
        self.assertFalse(ret_val)
        self.assertIs(rel_field._serializer_class, sc)

    def test_created_field(self):
        """Establish that explicitly asking for a `created` field
        does cause it to be included.
        """
        fc = test_serializers.CreatedSerializer()
        self.assertIn('created', fc.get_default_fields())

    def test_initial_data(self):
        """Establish that initial data is carried over to the `save_object`
        serializer method.
        """
        NormalModel = test_models.NormalModel

        # Create our child serializer.
        nm = NormalModel(id=42)
        ns = test_serializers.ChildSerializer(initial={
            'normal': nm.id,
        })

        # Establish that if we call `save_object` on a child that does not
        # yet have a normal, that the latter's presence in `initial` causes
        # it to be set on our object.
        cm = test_models.ChildModel()
        with self.assertRaises(ObjectDoesNotExist):
            cm.normal
        with mock.patch.object(BaseModelSerializer, 'save_object') as save:
            with mock.patch.object(NormalModel.objects, 'get') as get:
                get.return_value = nm

                # Actually perform the `save_object` call being tested.
                ns.save_object(cm)

                # Assert that the superclass `save_object` was called as
                # expected.
                save.assert_called_once_with(cm)

                # Assert that the `get` method was called as expected.
                get.assert_called_once_with(pk=42)
        self.assertEqual(cm.normal, nm)


class RelatedFieldTests(unittest.TestCase):
    def setUp(self):
        # Save my fake models to my test class.
        NormalModel = test_models.NormalModel
        self.nm = test_models.NormalModel
        self.cm = test_models.ChildModel

        # Set up related fields and things.
        self.rel_field = RelatedField(())
        self.rel_field.context = {}
        if hasattr(test_models.NormalModel.objects, 'get_queryset'):
            self.rel_field.queryset = NormalModel.objects.get_queryset()
        else:
            self.rel_field.queryset = NormalModel.objects.get_query_set()

    def test_related_field_from_id_dict(self):
        """Test that a related field's `from_native` method, when
        sent a dictionary with an `id` key, returns that ID.
        """
        # Test the case where we get a valid value back.
        with mock.patch.object(self.rel_field.queryset, 'get') as qs:
            qs.return_value = test_models.NormalModel(id=42)
            answer = self.rel_field.from_native({'id': 42 })
            qs.assert_called_with(id=42)
        self.assertEqual(answer, qs.return_value)

    def test_related_field_from_with_no_unique(self):
        """Test that a related field's `from_native` method, when
        no unique values are sent, raises ValidationError.
        """
        # Test the case where we get a valid value back.
        with self.assertRaises(ValidationError):
            answer = self.rel_field.from_native({'foo': 3 })

    def test_related_field_from_pk_noexist(self):
        """Test that a related field's `from_native` method processes
        a plain ID correctly, and processes DoesNotExist correctly.
        """
        # Test processing when DoesNotExist is raised.
        with mock.patch.object(self.rel_field.queryset, 'get') as m:
            m.side_effect = test_models.NormalModel.DoesNotExist
            with self.assertRaises(ValidationError):
                answer = self.rel_field.from_native(42)

    def test_related_field_from_pk_valueerror(self):
        """Test that a related field's `from_native` method processes
        a plain ID correctly, and processes ValueError correctly.
        """
        # Test processing when DoesNotExist is raised.
        with mock.patch.object(self.rel_field.queryset, 'get') as m:
            m.side_effect = ValueError
            with self.assertRaises(ValidationError):
                answer = self.rel_field.from_native(42)

    def test_related_field_from_unique_key(self):
        """Establish that we can retrieve a relation by a unique key within
        that model.
        """
        with mock.patch.object(self.rel_field.queryset, 'get') as m:
            answer = self.rel_field.from_native({'bacon': 42})
            m.assert_called_once_with(bacon=42)

    def test_related_field_from_composite_unique_keys(self):
        """Establish that we can retrieve a relation by a composite-unique
        set of keys within that model.
        """
        with mock.patch.object(self.rel_field.queryset, 'get') as m:
            answer = self.rel_field.from_native({'bar': 1, 'baz': 2})
            m.assert_called_once_with(bar=1, baz=2)

    def test_related_field_from_no_unique_keys(self):
        """Establish that if we attempt a lookup with no unique keys,
        that the system doesn't even try and raises an error.
        """
        with self.assertRaises(ValidationError):
            answer = self.rel_field.from_native({'foo': []})

    def test_related_field_from_bogus_field(self):
        """Establish that if I attempt to retrieve a related instance based on
        a field that does not exist on the related model, that ValidationError
        is raised.
        """
        with self.assertRaises(ValidationError):
            answer = self.rel_field.from_native({'bogus': None})

    def test_related_field_ignores_api_endpoint(self):
        """Establish that a `from_native` call will ignore serializer fields
        that do not correspond to model fields, such as `api_endpoint`.
        """
        with mock.patch.object(self.rel_field.queryset, 'get') as get:
            answer = self.rel_field.from_native({'api_endpoint': 1, 'baz': 2})
            get.assert_called_once_with(baz=2)

    def test_related_field_multiple_objects(self):
        """Establish that if I send criteria that don't narrow down to
        a single model instance, that ValidationError is raised.
        """
        with mock.patch.object(self.rel_field.queryset, 'get') as m:
            m.side_effect = test_models.NormalModel.MultipleObjectsReturned
            with self.assertRaises(ValidationError):
                answer = self.rel_field.from_native({'bar': 3})


@unittest.skipUnless(django_pgfields_installed, NO_DJANGOPG)
class PostgresFieldTests(unittest.TestCase):
    """Test suite to establish that the custom serializer fields that
    correlate to django_pg model fields work in the way we expect.
    """
    def test_uuid_field_no_auto_add(self):
        """Test that a UUID field without `auto_add` returns the
        correct serializer field.
        """
        # Instantiate my fake model serializer and establish that
        # we get back a UUIDField that is not read-only.
        s = test_serializers.PGFieldsSerializer()
        fields_dict = s.get_default_fields()
        self.assertIsInstance(fields_dict['uuid'], fields.UUIDField)
        self.assertEqual(fields_dict['uuid'].required, True)
        self.assertEqual(fields_dict['uuid'].read_only, False)

    def test_composite_field_without_drf_method(self):
        """Establish that we get a plain CompositeField if the model
        field does not instruct us otherwise.
        """
        s = test_serializers.PGFieldsSerializer()
        fields_dict = s.get_default_fields()
        self.assertEqual(fields_dict['coords'].__class__,
                         fields.CompositeField)

    def test_json_field_from_native(self):
        """Determine that a JSON serializer sends the value
        through on the `from_native` method.
        """
        jf = fields.JSONField()
        answer = jf.from_native([1, 3, 5])
        self.assertEqual(answer, [1, 3, 5])

    def test_json_field_to_native(self):
        """Determine that a JSON serializer sends the value
        through on the `to_native` method.
        """
        jf = fields.JSONField()
        answer = jf.to_native([1, 3, 5])
        self.assertEqual(answer, [1, 3, 5])

    def test_uuid_field_from_native(self):
        """Determine that the UUID serializer converts the value
        back to a Python UUID object.
        """
        uf = fields.UUIDField()
        answer = uf.from_native('01234567-0123-0123-0123-0123456789ab')
        self.assertIsInstance(answer, uuid.UUID)
        self.assertEqual(
            answer,
            uuid.UUID('01234567-0123-0123-0123-0123456789ab'),
        )

    def test_uuid_field_to_native(self):
        """Determine that the UUID serializer converts the value
        to a string representation of the uuid.
        """
        uf = fields.UUIDField()
        answer = uf.to_native(
            uuid.UUID('01234567-0123-0123-0123-0123456789ab'),
        )
        self.assertIsInstance(answer, six.text_type)
        self.assertEqual(answer, '01234567-0123-0123-0123-0123456789ab')

    def test_array_field_from_native(self):
        """Establish that the Array serializer converts the value
        back into a Python list as expected.
        """
        af = fields.ArrayField(of=serializers.IntegerField())
        answer = af.from_native([1, 1, '2', 3, '5', 8])
        self.assertIsInstance(answer, list)
        self.assertEqual(answer, [1, 1, 2, 3, 5, 8])

    def test_array_field_to_native(self):
        """Establish that the Array serializer converts the value
        to a Python list as expected.
        """
        af = fields.ArrayField(of=serializers.IntegerField())
        answer = af.to_native([1, 1, 2, 3, 5, 8])
        self.assertIsInstance(answer, list)
        self.assertEqual(answer, [1, 1, 2, 3, 5, 8])

    def test_composite_field_from_native(self):
        """Establish that the composite serializer converts the value
        back into the appropriate Python instance type.
        """
        # Create an instance class and composite field.
        Point = namedtuple('Point', ['x', 'y'])
        cf = fields.CompositeField(
            fields={
                'x': serializers.IntegerField(),
                'y': serializers.IntegerField(),
            },
            instance_class=Point,
        )

        # Test the conversion from a native dictionary.
        answer = cf.from_native({ 'x': 3, 'y': 1 })
        self.assertIsInstance(answer, Point)
        self.assertEqual(answer.x, 3)
        self.assertEqual(answer.y, 1)

    def test_composite_field_to_native(self):
        """Establish that the composite serializer converts the value
        back into the appropriate Python instance type.
        """
        # Create an instance class and composite field.
        Point = namedtuple('Point', ['x', 'y'])
        cf = fields.CompositeField(
            fields={
                'x': serializers.IntegerField(),
                'y': serializers.IntegerField(),
            },
            instance_class=Point,
        )

        # Test the conversion from a native dictionary.
        answer = cf.to_native(Point(x=3, y=1))
        self.assertIsInstance(answer, dict)
        self.assertEqual(answer, { 'x': 3, 'y': 1 })
