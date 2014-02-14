from __future__ import absolute_import, unicode_literals
from django.forms.widgets import Textarea
from drf_toolbox.utils import json



class JSONWidget(Textarea):
    """Subclass of forms.Textarea to render the value as JSON, rather than as
    the repr of the Python object.
    """
    def render(self, name, value, attrs=None):
        return super(JSONWidget, self).render(
            name,
            json.dumps(value, indent=4, sort_keys=True),
            attrs,
        )
