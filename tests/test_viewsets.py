from __future__ import absolute_import, unicode_literals
from django.test.client import RequestFactory
from drf_toolbox import serializers
from drf_toolbox.compat import django_pgfields_installed, models
from drf_toolbox.viewsets import ModelViewSet
from rest_framework.request import Request
from rest_framework.decorators import link
from tests import models as test_models
from tests.compat import mock
from tests.views import *
import unittest
import uuid


NO_DJANGOPG = 'django-pgfields is not installed.'


class ModelViewSetTests(unittest.TestCase):
    """A set of tests to establish that the ModelViewSet subclass works
    as expected.
    """
    def setUp(self):
        self.request = Request(RequestFactory().get('/foo/'))

    def test_get_queryset(self):
        """Establish that our `get_queryset` method filters in the
        way we expect.
        """
        mvs = ModelViewSet()
        with mock.patch.object(ModelViewSet.mro()[1], 'get_queryset') as m:
            qs = mvs.get_queryset()
            self.assertEqual(qs, m.return_value)

    def test_get_queryset_with_kwargs(self):
        """Establish that our `get_queryset` method filters in the way
        we expect if we have unknown keyword arguments (which typically come
        from parent viewsets).
        """
        mvs = ModelViewSet(kwargs={'foo__pk': 42})
        with mock.patch.object(ModelViewSet.mro()[1], 'get_queryset') as m:
            m.return_value = mock.MagicMock()
            qs = mvs.get_queryset()
            self.assertEqual(m.return_value.mock_calls,
                             [mock.call.filter(foo__pk=42)])

    def test_get_serializer(self):
        """Establish that our `get_serializer` method returns a
        correctly-created serializer class.
        """
        class ViewSet(ModelViewSet):
            model = test_models.NormalModel

            @link()
            def foo(self, request, pk):
                return 'irrelevant'

        vs = ViewSet(request=self.request, kwargs={}, format_kwarg='format')
        serializer = vs.get_serializer()
        self.assertIsInstance(serializer, serializers.ModelSerializer)
        self.assertEqual(serializer.context['child_endpoints'], ['foo'])

    def test_parser_classes_standard(self):
        """Establish that our `parser_classes` property works as
        expected, and gives the usual parsers from settings if there
        are no composite fields.
        """
        vs = NormalViewSet(
            request=RequestFactory().options('/foo/',
                                             HTTP_ACCEPT='application/json'),
            format_kwarg='format',
        )
        result = vs.options(self.request)
        self.assertEqual(result.data['parses'], [
            'application/json',
            'application/x-www-form-urlencoded',
            'multipart/form-data',
        ])

    @unittest.skipUnless(django_pgfields_installed, NO_DJANGOPG)
    def test_parser_classes_with_composite_field(self):
        """Establish that our `parser_classes` property works as
        expected, and removes HTML form inputs if there is a composite field
        present.
        """
        class CompositeModel(models.Model):
            foo = test_models.CoordsField()
            class Meta:
                app_label = 'dfghgfdhfgh'

        class CompositeViewSet(ModelViewSet):
            model = CompositeModel

        cvs = CompositeViewSet(
            request=RequestFactory().options('/foo/',
                                             HTTP_ACCEPT='application/json'),
            format_kwarg='format',
        )
        result = cvs.options(self.request)
        self.assertEqual(result.data['parses'], ['application/json'])

    @unittest.skipUnless(django_pgfields_installed, NO_DJANGOPG)
    def test_parser_classes_with_special_composite_field(self):
        """Establish that our `parser_classes` property works as
        expected, and still removes HTML if it gets a custom class
        that does not disable that behavior.
        """
        class CompositeModel(models.Model):
            foo = test_models.SizeField()
            class Meta:
                app_label = 'tryeytry'

        class CompositeViewSet(ModelViewSet):
            model = CompositeModel

        cvs = CompositeViewSet(
            request=RequestFactory().options('/foo/',
                                             HTTP_ACCEPT='application/json'),
            format_kwarg='format',
        )
        result = cvs.options(self.request)
        self.assertEqual(result.data['parses'], ['application/json'])

    @unittest.skipUnless(django_pgfields_installed, NO_DJANGOPG)
    def test_parser_classes_with_special_composite_field_passthrough(self):
        """Establish that our `parser_classes` property works as
        expected, and does **not** remove HTML if the serializer field
        says it is not necessary.
        """
        class CompositeModel(models.Model):
            foo = test_models.SizeField()
            class Meta:
                app_label = 'cndfgh'

        class CompositeViewSet(ModelViewSet):
            model = CompositeModel

        try:
            test_models.SizeSerializerField.suppress_form_parsing = False
            cvs = CompositeViewSet(
                request=RequestFactory().options('/foo/',
                                                 HTTP_ACCEPT='application/json'),
                format_kwarg='format',
            )
            result = cvs.options(self.request)
            self.assertEqual(result.data['parses'], [
                'application/json',
                'application/x-www-form-urlencoded',
                'multipart/form-data',
            ])
        finally:
            test_models.SizeSerializerField.suppress_form_parsing = True

    def test_get_serializer_nested(self):
        """Establish that our `get_serializer` method works on a
        nested viewset, and returns a correctly-created serializer class.
        """
        fmjvs = ChildViewSet(request=self.request,
                             kwargs={'normal__pk': '42'},
                             format_kwarg='format')
        serializer = fmjvs.get_serializer()
        self.assertIsInstance(serializer, serializers.ModelSerializer)
        self.assertTrue(serializer.fields['normal'].read_only)
        self.assertFalse(serializer.fields['normal'].required)
        self.assertEqual(serializer._initial, {'normal': '42'})

    def test_get_serializer_random_kwarg(self):
        """Establish that our `get_serializer` method correctly ignores
        a keyword argument that it doesn't know what to do with.
        """
        class ViewSet(ModelViewSet):
            model = test_models.NormalModel

        vs = ViewSet(request=self.request, kwargs={'foo': 'bar'},
                     format_kwarg='format')
        serializer = vs.get_serializer()
        self.assertIsInstance(serializer, serializers.ModelSerializer)
        self.assertEqual(serializer._initial, {})

    def test_get_serializer_double_nested_kwarg(self):
        """Establish that `get_serializer` doesn't add double-nested
        keyword arguments to initial data.
        """
        class ViewSet(ModelViewSet):
            model = test_models.NormalModel

        vs = ViewSet(request=self.request, kwargs={'foo__bar__pk': 'baz'},
                     format_kwarg='format')
        serializer = vs.get_serializer()
        self.assertIsInstance(serializer, serializers.ModelSerializer)
        self.assertEqual(serializer._initial, {})

    def test_get_serializer_excluded_nested_field(self):
        """Establish that if we are excluding from display the field that
        is the nesting agent, that we still get what we want.
        """
        cvs3 = ChildViewSetIII(request=self.request,
                               kwargs={'normal__pk': 'foobar'},
                               format_kwarg='format')
        serializer = cvs3.get_serializer()
        self.assertIsInstance(serializer, serializers.ModelSerializer)
        self.assertEqual(serializer._initial, {'normal': 'foobar'})

    def test_get_serializer_with_problematic_model_serializer(self):
        """Establish that a viewset that uses a serializer that is not
        a ModelSerializer subclass raises TypeError if anything triggering
        `initial` is used.
        """
        # Create my serializer class and viewset.
        class BadFakeSerializer(object):
            pass
        class ViewSet(ModelViewSet):
            model = test_models.NormalModel
            serializer_class = BadFakeSerializer

        # Attempt to get the serializer for this viewset.
        vs = ViewSet(request=self.request,
                     kwargs={'foo__pk': 'bar'},
                     format_kwarg='format')
        with self.assertRaises(TypeError):
            serializer = vs.get_serializer()
