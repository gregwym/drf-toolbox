from __future__ import absolute_import, unicode_literals
from django.conf import settings
import os
import sys
import unittest


# Ensure that the drf-toolbox directory is part of our Python path.
APP_ROOT = os.path.realpath(os.path.dirname(__file__) + '/../')
sys.path.insert(0, APP_ROOT)


def load_tests(loader, standard_tests, throwaway):
    return loader.discover(
        start_dir=os.path.realpath(os.path.dirname(__file__)),
    )


# Configure basic settings.
settings.configure(
    ALLOWED_HOSTS=['testserver'],
    REST_FRAMEWORK={
        'DEFAULT_MODEL_SERIALIZER_CLASS': 
            'drf_toolbox.serializers.ModelSerializer',
        'DEFAULT_RENDERER_CLASSES': (
            'drf_toolbox.renderers.APIRenderer',
            'drf_toolbox.renderers.JSONRenderer',
            'drf_toolbox.renderers.JSONPRenderer',
            # 'rest_framework.renderers.XMLRenderer',
            'rest_framework.renderers.YAMLRenderer',
        ),
    },
    ROOT_URLCONF='tests.urls',
)

# Actually run the tests.
if __name__ == '__main__':
    unittest.main()
