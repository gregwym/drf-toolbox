from __future__ import absolute_import, unicode_literals
from django import forms
from django.conf import settings
from django.test.client import RequestFactory
from django.template import loader, Template
from drf_toolbox.renderers import APIRenderer
from rest_framework import generics, serializers, viewsets
from rest_framework.renderers import BrowsableAPIRenderer 
from rest_framework.request import Request
from tests.compat import mock
import unittest


class RendererTests(unittest.TestCase):
    """A test suite to ensure that the renderer for Django REST Framework
    that is included with DRF Toolbox works as expected.
    """
    def setUp(self):
        self.request = Request(RequestFactory().get('/something/'))
        self.renderer = APIRenderer()
        self.renderer.accepted_media_type = 'text/html'
        self.renderer.renderer_context = {
            'request': self.request,
        }

    def test_render_method(self):
        """Test that the DRF Toolbox renderer adds a version number
        and calls the superclass renderer.
        """
        with mock.patch.object(settings, 'VERSION',
                               create=True, new='24.60.1'):
            with mock.patch.object(BrowsableAPIRenderer, 'render') as m:
                self.renderer.render('foo', 'application/json', {})
                m.assert_called_with('foo', 'application/json', {
                    'version': '24.60.1',
                })
