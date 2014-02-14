from __future__ import absolute_import, unicode_literals
from django.test.client import RequestFactory
from drf_toolbox.serializers.fields.api import *
from rest_framework.request import Request
from tests.compat import mock
from tests.models import *
import unittest
import uuid


class APIEndpointTests(unittest.TestCase):
    """Establish that the APIEndpointsField class works as
    expected.
    """
    def setUp(self):
        self.aef = APIEndpointsField()
        self.aef.context = {'request': Request(RequestFactory().get('/foo/'))}

    def test_no_url_in_field_to_native_singular(self):
        """Establish that if we get a falsy value back from `_get_base_url`,
        that the `field_to_native` method returns None.
        """
        aef_singular = APIEndpointField()
        with mock.patch.object(aef_singular, '_get_base_url') as gbu:
            gbu.return_value = None
            self.assertEqual(aef_singular.field_to_native(None, 'api_endpoint'),
                             None)

    def test_no_get_absolute_url(self):
        """Establish that if there is no `get_absolute_url` method on the
        model, that we return None.
        """
        fm = ExplicitAPIEndpointsModel()
        self.assertEqual(self.aef.field_to_native(fm, 'irrelevant'), {})

    def test_no_host(self):
        """Establish that if there is no request host, that we just get
        the URI of the model in the result.
        """
        m = NormalModel(id=42)
        with mock.patch.object(self.aef.context['request'], 'get_host') as gh:
            gh.return_value = None
            endpoints = self.aef.field_to_native(m, 'irrelevant')
        self.assertEqual(endpoints, {'self': '/normal/%d/' % m.id})

    def test_child_endpoints(self):
        """Establish that if `child_endpoints` is present on the request's
        context, that these endpoints are included in the APIEndpointsField
        output.
        """
        m = NormalModel(id=42)
        with mock.patch.dict(self.aef.context, child_endpoints={'foo', 'bar'}):
            endpoints = self.aef.field_to_native(m, 'irrelevant')            
        self.assertEqual(endpoints, {
            'self': 'http://testserver/normal/%s/' % m.id,
            'foo': 'http://testserver/normal/%s/foo/' % m.id,
            'bar': 'http://testserver/normal/%s/bar/' % m.id,
        })

    def test_unhonored_child_endpoints(self):
        """Establish that if a field is initialized and child endpoints
        are not yet present, that we do not honor them if they show up
        in the context later.
        """
        # We need a separate APIEndpointsField object for this test,
        # since I don't want to take destructive action on the one attached
        # to this TestCase subclass.
        aef = APIEndpointsField()
        aef.context = {}
        with mock.patch.object(APIEndpointField, 'initialize') as init:
            aef.initialize(None, 'api_endpoints')
            init.assert_called_once_with(field_name='api_endpoints',
                                         parent=None)
            self.assertFalse(aef._honor_child_endpoints)

        # Add child endpoints, and establish that they are ignored when
        # `field_to_native` is called.
        aef.context = {'child_endpoints': ['foo', 'bar']}
        with mock.patch.object(aef, '_get_base_url') as gbu:
            gbu.return_value = 'http://foo.com/bar/'
            fields = aef.field_to_native(object(), 'api_endpoints')
        self.assertIn('self', fields)
        self.assertNotIn('foo', fields)
        self.assertNotIn('bar', fields)

    def test_honored_child_endpoints(self):
        """Establish that if a field is initialized after child endpoints
        are already present in the context, that they are honored.
        """
        # We need a separate APIEndpointsField object for this test,
        # since I don't want to take destructive action on the one attached
        # to this TestCase subclass.
        aef = APIEndpointsField()
        aef.context = {'child_endpoints': ['foo', 'bar']}
        with mock.patch.object(APIEndpointField, 'initialize') as init:
            aef.initialize(None, 'api_endpoints')
            init.assert_called_once_with(field_name='api_endpoints',
                                         parent=None)
            self.assertTrue(aef._honor_child_endpoints)

        # Add child endpoints, and establish that they are ignored when
        # `field_to_native` is called.
        with mock.patch.object(aef, '_get_base_url') as gbu:
            gbu.return_value = 'http://foo.com/bar/'
            fields = aef.field_to_native(object(), 'api_endpoints')
        self.assertIn('self', fields)
        self.assertIn('foo', fields)
        self.assertIn('bar', fields)        

    def test_format(self):
        """Establish that if a format is available in the context, that it
        is similarly used in the output.
        """
        m = NormalModel(id=42)
        with mock.patch.dict(self.aef.context, format='json'):
            endpoints = self.aef.field_to_native(m, 'irrelevant')            
        self.assertEqual(endpoints, {
            'self': 'http://testserver/normal/%d.json' % m.id,
        })

