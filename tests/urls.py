from __future__ import absolute_import, unicode_literals
from django.conf.urls import patterns, include, url
from drf_toolbox import routers
import tests.views

router = routers.Router()
router.register(r'normal', 'tests.views.NormalViewSet')
router.register(r'child', 'tests.views.ChildViewSet')
router.register(r'rel', tests.views.FakeRelModelViewSet)


urlpatterns = patterns('',
    # REST API Framework
    url(r'^auth/', include('rest_framework.urls', namespace='rest_framework')),
    url('', include(router.urls)),
)
