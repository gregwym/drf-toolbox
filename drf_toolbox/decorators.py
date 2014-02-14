from __future__ import unicode_literals
from rest_framework.decorators import action, link


def base_action(methods=['POST'], **kwargs):
    """A decorator to cause a method to be routed as a "base action" in
    Django REST Framework, meaning it doesn't expect to operate on
    a specific model instance.
    """
    def decorator(func):
        func.base_http_methods = methods
        func.kwargs = kwargs
        return func
    return decorator
