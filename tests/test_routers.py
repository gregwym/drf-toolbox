from __future__ import absolute_import, unicode_literals
from drf_toolbox import routers
from drf_toolbox.compat import models, django_pgfields_installed
from drf_toolbox.decorators import base_action
from rest_framework import viewsets
from tests.compat import mock
from tests.views import NormalViewSet
import six
import unittest


class RouterTests(unittest.TestCase):
    """A series of tests to establish that my REST Framework Router
    functions as it should.
    """
    def test_router_urls(self):
        """Establish that a router with a viewset attached gets the
        expected URLs.
        """
        # Create a model and viewset with at least one special method.
        class PhonyModel(models.Model):
            class Meta:
                app_label = 'tests'

        class PhonyViewSet(viewsets.ModelViewSet):
            model = PhonyModel

            @base_action({ 'POST' })
            def special(self, request):
                pass

        # Create the router and register our viewset.
        with mock.patch('drf_toolbox.routers.ModelSerializer'):
            router = routers.Router()
        router.register('phony', PhonyViewSet)

        # Attempt to establish that we got back what we expected.
        for urlpattern in router.urls:
            pattern = urlpattern.regex.pattern
            integer_regex = routers.integer_regex
            if '<pk>' in pattern:
                self.assertIn('(?P<pk>%s)' % integer_regex.pattern, pattern)
            if '<format>' in urlpattern.regex.pattern:
                self.assertFalse(pattern.endswith(r'/\.(?P<format>[a-z]+)$'))

    @unittest.skipUnless(django_pgfields_installed,
                         'django-pgfields is not installed.')
    def test_router_urls_uuid(self):
        """Establish that a router with a viewset attached gets the
        expected URLs.
        """
        # Create a model and viewset with at least one special method.
        class PhonyModelII(models.Model):
            id = models.UUIDField(auto_add=True, primary_key=True)
            class Meta:
                app_label = 'tests'

        class PhonyViewSetII(viewsets.ModelViewSet):
            model = PhonyModelII

            @base_action({ 'POST' })
            def special(self, request):
                pass

        # Create the router and register our viewset.
        with mock.patch('drf_toolbox.routers.ModelSerializer'):
            router = routers.Router()
        router.register('phony', PhonyViewSetII)

        # Attempt to establish that we got back what we expected.
        for urlpattern in router.urls:
            pattern = urlpattern.regex.pattern
            uuid_regex = routers.uuid_regex
            if '<pk>' in pattern:
                self.assertIn('(?P<pk>%s)' % uuid_regex.pattern, pattern)
            if '<format>' in urlpattern.regex.pattern:
                self.assertFalse(pattern.endswith(r'/\.(?P<format>[a-z]+)$'))

    def test_router_urls_with_custom_lookup_field(self):
        """Establish that a router with a viewset attached gets
        expected URLs.
        """
        # Create a model and viewset with a special lookup field.
        class PhonyModelIII(models.Model):
            class Meta:
                app_label = 'tests'

        class PhonyViewSetIII(viewsets.ModelViewSet):
            model = PhonyModelIII
            lookup_field = 'foo'

            @base_action({ 'POST' })
            def special(self, request):
                pass

        # Create the router and register our viewset.
        with mock.patch('drf_toolbox.routers.ModelSerializer'):
            router = routers.Router()
        router.register('phony', PhonyViewSetIII)

        # Attempt to establish that we got back what we expected.
        for urlpattern in router.urls:
            pattern = urlpattern.regex.pattern
            base_regex = routers.base_regex
            if '<foo>' in pattern:
                self.assertIn('(?P<foo>%s)' % base_regex.pattern, pattern)
            if '<format>' in urlpattern.regex.pattern:
                self.assertFalse(pattern.endswith(r'/\.(?P<format>[a-z]+)$'))

    def test_router_urls_with_custom_lookup_regex(self):
        """Establish that a router with a viewset attached gets
        expected URLs when the viewset has a custom regex.
        """
        # Create a model and viewset with a special lookup field.
        class PhonyModelIV(models.Model):
            class Meta:
                app_label = 'tests'

        class PhonyViewSetIV(viewsets.ModelViewSet):
            model = PhonyModelIV
            lookup_regex = '[0123456789]+'

            @base_action({ 'POST' })
            def special(self, request):
                pass

        # Create the router and register our viewset.
        with mock.patch('drf_toolbox.routers.ModelSerializer'):
            router = routers.Router()
        router.register('phony', PhonyViewSetIV)

        # Attempt to establish that we got back what we expected.
        for urlpattern in router.urls:
            pattern = urlpattern.regex.pattern
            if '<pk>' in pattern:
                self.assertIn('(?P<pk>[0123456789]+)', pattern)
            if '<format>' in urlpattern.regex.pattern:
                self.assertFalse(pattern.endswith(r'/\.(?P<format>[a-z]+)$'))

    def test_parent_mismatch(self):
        """Establish that instantiating a Router with only one of
        `parent` and `parent_prefix` raises ValueError.
        """
        with self.assertRaises(ValueError):
            routers.Router(parent_prefix='foo')

    def test_bytestring_resolution(self):
        """Establish that if we get a byte-string as an argument to
        router.register, that we still correctly resolve the model.
        """
        router = routers.Router()
        router.register('normal', b'tests.views.NormalViewSet')
        self.assertEqual(
            router.registry,
            [('normal', NormalViewSet, 'normalmodel')],
        )

    def test_child_router_creation(self):
        """Establish that registering a nested viewset causes a child
        router to be created.
        """
        # Set up our routers.
        router = routers.Router()
        router.register('unrelated', 'tests.views.ExplicitAPIEndpointsViewSet')
        router.register('normal', 'tests.views.NormalViewSet')
        router.register('normal/child', 'tests.views.ChildViewSet')

        # Establish that the base router has one route and one child.
        self.assertEqual(len(router.registry), 2)
        self.assertIn('normal', router.children)
        self.assertIsInstance(router.children['normal'], routers.Router)

    def test_child_router_creation_nested(self):
        """Establish that registering a nested viewset causes a child
        to be created, including from child routers.
        """
        # Set up our routers.
        router = routers.Router()
        router.register('normal', 'tests.views.NormalViewSet')
        router.register('normal/child', 'tests.views.ChildViewSet')
        router.register('normal/child/grandchild',
                        'tests.views.GrandchildViewSet')

        # Establish that there is a grandchild router.
        grandchild = router.children['normal'].children['child']
        self.assertIsInstance(grandchild, routers.Router)

        # Get the routes from the parent router, and establish that
        # the grandchild routes are formatted as we expect.
        routes = grandchild.get_preformatted_routes()
        self.assertEqual(routes[0].url,
            r'^normal/(?P<childmodel__normalmodel__pk>[0-9]+)'
            r'/child/(?P<childmodel__pk>[0-9]+)/{prefix}'
            r'{trailing_slash}$',
        )

    def test_child_creation_with_no_parent(self):
        """Establish that registering a nested viewset that would cause
        a child router to be created fails if the parent prefix has not
        yet been registered.
        """
        # Set up our routers...and fail.
        router = routers.Router()
        with self.assertRaises(ValueError):
            router.register('normal/child', 'tests.views.ChildViewSet')

    def test_child_urls(self):
        """Establish that the router `get_urls` method will also
        include URLs from its child routers.
        """
        # Set up our routers.
        router = routers.Router()
        router.register('normal', 'tests.views.NormalViewSet')
        router.register('normal/child', 'tests.views.ChildViewSet')

        # Get the URLs from the parent router.
        urls = router.get_urls()
        self.assertEqual([i.regex.pattern for i in urls], [
            r'^$',
            r'^\.(?P<format>[a-z0-9]+)$',
            r'^normal/$',
            r'^normal\.(?P<format>[a-z0-9]+)$',
            r'^normal/(?P<pk>[0-9]+)/$',
            r'^normal/(?P<pk>[0-9]+)\.(?P<format>[a-z0-9]+)$',
            r'^normal/(?P<normalmodel__pk>[0-9]+)/child/$',
            '/'.join((
                r'^normal/(?P<normalmodel__pk>[0-9]+)',
                r'child\.(?P<format>[a-z0-9]+)$',
            )),
            '/'.join((
                r'^normal/(?P<normalmodel__pk>[0-9]+)',
                r'child/(?P<pk>[0-9]+)/$',
            )),
            '/'.join((
                r'^normal/(?P<normalmodel__pk>[0-9]+)',
                r'child/(?P<pk>[0-9]+)\.(?P<format>[a-z0-9]+)$',
            )),
        ])

    def test_get_viewset_by_prefix_fail(self):
        """Establish that if we attempt to get a viewset by prefix and the
        prefix is not actually registered on the router, that we raise
        KeyError.
        """
        router = routers.Router()
        with self.assertRaises(KeyError):
            router.get_viewset_by_prefix('nope')
