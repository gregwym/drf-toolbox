from __future__ import absolute_import, unicode_literals
from copy import copy
from drf_toolbox.serializers import ModelSerializer
from importlib import import_module
from rest_framework import routers
from rest_framework.compat import url
from rest_framework.settings import api_settings
import re
import six


uuid_regex = re.compile(r'[0-9a-f-]{36}')


class Router(routers.DefaultRouter):
    """DefaultRouter subclass that is slightly smarter about precisely
    routing URLs to views.
    """
    def __init__(self, parent=None, parent_prefix=None,
                       *args, **kwargs):
        if not parent:
            ModelSerializer._router = self
        super(Router, self).__init__(*args, **kwargs)

        # Track this router's ancestry and descendents, as some routers
        # are owned by other routers.
        self.parent = parent
        self.parent_prefix = parent_prefix
        self.parent_viewset = None
        self.children = {}

        # Sanity check: Either both or neither of parent_router and
        # parent_prefix must be defined.
        if bool(parent) ^ bool(parent_prefix):
            raise ValueError('Either both or neither of `parent` and '
                             '`parent_prefix` must be defined.')

        # If a parent_prefix was provided, it must correspond to an
        # already-registered prefix on the parent, and we need to
        # register the corresponding parent viewset.
        if parent_prefix:
            parent_validated = False
            for prefix, viewset, base_name in parent.registry:
                if parent_prefix == prefix:
                    parent_validated = True
                    self.parent_viewset = viewset

            # If we failed to find a matching prefix, raise an Exception.
            if not parent_validated:
                raise ValueError('Parent prefix must correspond to a prefix '
                                 'already registered on the router.')

        # If a parent is provided, add this object to its `children`
        # dictionary.
        if parent:
            self.parent.children[parent_prefix] = self

    @property
    def routes(self):
        """Return the appropriate base routes for this router,
        ready to be substituted by `get_routes`.
        """
        return self.get_preformatted_routes()

    def get_lookup_regex(self, viewset, lookup_prefix=''):
        """Return a regular expression that correctly checks
        for a UUID as a PK value.
        """
        # Determine the appropriate lookup field.
        lookup_field = getattr(viewset, 'lookup_field', 'pk')
        if lookup_prefix:
            lookup_field = '%s__%s' % (lookup_prefix, lookup_field)

        # Generate the regex to return.
        return r'(?P<{lookup_field}>{uuid})'.format(
            lookup_field=lookup_field,
            uuid=uuid_regex.pattern,
        )

    def get_preformatted_routes(self, recursive_prefix=''):
        """Return a tuple of routes ready to be formatted.
        This is the initial input for the `get_routes` method.
        """
        # If this router is not a child of another router,
        # the superclass routes are fine.
        if not self.parent:
            return super(Router, self).routes

        # We need to determine the appropriate singular noun of the parent,
        # because we need to replace `pk` with `noun__pk` in the regex
        # to avoid duplicating the backreference name.
        lookup_prefix = getattr(self.parent_viewset, 'base_name',
            self.get_default_base_name(self.parent_viewset),
        )
        if recursive_prefix:
            lookup_prefix = '%s__%s' % (recursive_prefix, lookup_prefix)

        # This router is the child of another router; that means
        # that it must be prefixed with the detail route from the
        # parent router.
        parent_routes = self.parent.get_preformatted_routes(lookup_prefix)
        parent_url_prefix = parent_routes[1].url.format(
            prefix=self.parent_prefix,
            lookup=self.parent.get_lookup_regex(self.parent_viewset,
                lookup_prefix=lookup_prefix,
            ),
            trailing_slash='/',
        ).rstrip('$').replace('{', '{{').replace('}', '}}')

        # Generate Route tuples corresponding to the parent's route tuples,
        # but with the parent prefix prepended.
        answer = []
        for route in super(Router, self).routes:
            answer.append(routers.Route(
                url=parent_url_prefix + route.url.lstrip('^'),
                mapping=route.mapping,
                name=route.name,
                initkwargs=route.initkwargs,
            ))
        return answer

    def get_routes(self, viewset):
        """Return a list of routers.Route namedtuples that correspond
        to the routes for the given viewset.
        """
        answer = super(Router, self).get_routes(viewset)

        # Iterate over the methods on the viewset and look for any
        # base methods.
        #
        # Note: We have a confusing situation here because the use of the
        # term "method" is overloaded; it refers both to HTTP methods
        # (e.g. GET, POST) and class/instance methods in Python.  In order
        # to try and gain some clarity, the former are consistently referred
        # to in this code block as "HTTP methods".
        for method_name in dir(viewset):
            method = getattr(viewset, method_name)

            # Sanity check: If this viewset method doesn't have a
            # `base_http_methods` attribute, we're done.
            if not hasattr(method, 'base_http_methods'):
                continue

            # Determine the HTTP methods, URL pattern, and name pattern.
            http_methods = [i.lower() for i in method.base_http_methods]
            url_format = r'^{prefix}/{methodname}{trailing_slash}$'
            url = routers.replace_methodname(url_format, method_name)
            name_format = '{basename}-{methodnamehyphen}' 
            name = routers.replace_methodname(name_format, method_name)

            # Create the actual Route object.
            route = routers.Route(
                url=url,
                mapping=dict([(i, method_name) for i in http_methods]),
                name=name,
                initkwargs=copy(method.kwargs),
            )

            # Append the route to the answer.
            answer.append(route)

        # Done!
        return answer

    def get_urls(self):
        """Return a list of URL patterns, including a default root view
        for the API, and appending format suffixes.

        Unlike the superclass method, ensure that format suffixes also
        strip trailing slashes.
        """
        answer = []

        # Add all urlpatterns from the superclass method to the answer,
        # but modify the .format URL to expunge the trailing slash.
        for urlpattern in super(Router, self).get_urls():
            if '/\\.(?P<format>' in urlpattern.regex.pattern:
                answer.append(url(
                    urlpattern.regex.pattern.replace('/\\.(?P<format>',
                                                     '\\.(?P<format>'),
                    urlpattern._callback or urlpattern._callback_str,
                    urlpattern.default_args,
                    urlpattern.name,
                ))
            else:
                answer.append(urlpattern)

        # Any urlpatterns defined by child routers should also
        # be included here.
        for prefix, child in self.children.items():
            for urlpattern in child.get_urls():
                answer.append(urlpattern)

        # Done; return the final answer.
        return answer

    def get_viewset_by_prefix(self, needle):
        """Return the viewset corresponding to the prefix that has
        previously been registered on this router.

        If no such viewset is found, raise KeyError.
        """
        for prefix, viewset, base_name in self.registry:
            if prefix == needle:
                return viewset
        raise KeyError('No prefix `%s` has been registered.' % needle)

    def register(self, prefix, viewset, base_name=None):
        """Register a viewset to this router, at the given URL prefix,
        and with the given base name if one is provided.
        """
        # The viewset may be specified as a string rather than
        # a ViewSet object; resolve it into an object.
        viewset = self._resolve_viewset(viewset)

        # The prefix may be specified in a nested format.  If so, parse
        # it out and register and return a child router.
        if '/' in prefix:
            routers = [self]
            for token in prefix.split('/')[:-1]:
                try:
                    routers.append(routers[-1].children[token])
                except KeyError:
                    new_router = type(self)(parent=routers[-1],
                                            parent_prefix=token)
                    new_router.include_root_view = False
                    routers.append(new_router)

            # Get the name of the penultimate and final prefix in use.
            penult_prefix, final_prefix = prefix.split('/')[-2:]

            # Take the penultimate router, and find the viewset that is
            # the direct parent of this one.
            parent_viewset = routers[-2].get_viewset_by_prefix(penult_prefix)
            if not hasattr(parent_viewset, 'children'):
                parent_viewset.children = {}
            parent_viewset.children[final_prefix] = viewset

            # Perform this registration against the child router.
            return routers[-1].register(final_prefix, viewset,
                                        base_name=base_name)

        # Perform standard registration.
        return super(Router, self).register(prefix, viewset, base_name)

    def _resolve_viewset(self, viewset):
        """If a viewset has been provided as a dot-path in a string, return
        the corresponding object.
        """
        # Sanity check: If we got a bytes string (an easy mistake to make
        # in Python 2), convert it to a text string.
        if isinstance(viewset, six.binary_type):
            viewset = viewset.decode('utf-8')

        # If we got a text string, resolve the viewset and get the actual
        # class.
        if isinstance(viewset, six.text_type):
            # Determine the full module name and the class name.
            module_name = '.'.join(viewset.split('.')[0:-1])
            class_name = viewset.split('.')[-1]

            # Import the module.
            module = import_module(module_name)

            # Return the class.
            return getattr(module, class_name)
        return viewset
