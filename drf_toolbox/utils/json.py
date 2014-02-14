from __future__ import absolute_import, unicode_literals
from drf_toolbox.renderers.json import JSONEncoder
from functools import wraps
import json


@wraps(json.dump)
def dump(value, fp, *args, **kwargs):
    kwargs.setdefault('cls', JSONEncoder)
    return json.dump(value, fp, *args, **kwargs)


@wraps(json.dumps)
def dumps(value, *args, **kwargs):
    kwargs.setdefault('cls', JSONEncoder)
    return json.dumps(value, *args, **kwargs)


from json import JSONDecoder, load, loads
