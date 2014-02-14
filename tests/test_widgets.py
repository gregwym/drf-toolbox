from __future__ import absolute_import, unicode_literals
from drf_toolbox.serializers.widgets import JSONWidget
import unittest


class JSONWidgetTests(unittest.TestCase):
    """A set of tests to ensure that the JSONWidget object works in
    the way we expect.
    """
    def test_render(self):
        jw = JSONWidget()
        html = jw.render('foo', {'foo': 'bar', 'spam': 'eggs'})
        self.assertIn('<textarea cols="40" name="foo" rows="10">', html)
        self.assertIn('&quot;foo&quot;: &quot;bar&quot;', html)
        self.assertIn('&quot;spam&quot;: &quot;eggs&quot;', html)
        self.assertIn('</textarea>', html)
