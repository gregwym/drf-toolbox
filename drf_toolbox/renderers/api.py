from __future__ import absolute_import, unicode_literals
from django import forms
from django.conf import settings
from django.template import loader, RequestContext
from rest_framework.renderers import BrowsableAPIRenderer, HTMLFormRenderer
import collections


class APIRenderer(BrowsableAPIRenderer):
    """BrowsableAPIRenderer subclass that adds the settings.VERSION
    to the context, if it's present.
    """
    def render(self, data, media_type, renderer_context):
        renderer_context['version'] = getattr(settings, 'VERSION', '')
        return super(APIRenderer, self).render(data, media_type,
                                               renderer_context)

