from __future__ import absolute_import, unicode_literals
from datetime import datetime, date, time, timedelta
from drf_toolbox.renderers.json import JSONEncoder
from drf_toolbox.utils import json
from sdict import adict
import decimal
import pytz
import six
import unittest


class JSONTests(unittest.TestCase):
    """A test suite for testing the custom JSON classes provided
    by Torch.
    """
    def test_dumps(self):
        """Ensure that json.dumps dumps both new things (datetime)
        and old things (string, bool) correctly.
        """
        # Define the data to be dumped.
        d = adict({
            'a': datetime(2012, 4, 21, 16, tzinfo=pytz.UTC),
            'b': True,
            'c': 'foo',
        })

        # Dump the data, and verify the dump.
        payload = json.dumps(d)
        self.assertEqual(
            payload,
            '{"a": 1335024000, "b": true, "c": "foo"}',
        )

    def test_invalid_input(self):
        """Test that invalid input still raises TypeError as
        we expect.
        """
        d = object()
        with self.assertRaises(TypeError):
            json.dumps(d)

    def test_dump(self):
        """Ensure that json.dump still sends output to a file-like
        object as I expect.
        """
        try:
            # Set up my fake file and my data.
            f = six.StringIO()
            d = { 'a': datetime(2012, 4, 21, 16, tzinfo=pytz.UTC) }

            # Perform the dump.
            json.dump(d, f)

            # Verify that I got what I expected.
            payload = f.getvalue()
            self.assertEqual(payload, '{"a": 1335024000}')
        finally:
            f.close()

    def test_dump_date(self):
        """Establish that JSON dumping a date works as expected."""
        d = date(2012, 4, 21)
        self.assertEqual(json.dumps(d), '"2012-04-21"')

    def test_dump_time(self):
        """Establish that JSON dumping a time works as expected."""
        t = time(12, 0, 0)
        self.assertEqual(json.dumps(t), '"12:00:00"')

    def test_dump_time_with_microseconds(self):
        """Establish that JSON dumping a time with microseconds works
        as expected.
        """
        t = time(12, 0, 0, 1000)
        self.assertEqual(json.dumps(t), '"12:00:00.001"')

    def test_dump_aware_time(self):
        """Establish that JSON dumping a timezone aware time produces
        an error.
        """
        t = time(12, 0, 0, tzinfo=pytz.UTC)
        with self.assertRaises(ValueError):
            json.dumps(t)

    def test_dump_timedelta(self):
        """Establish that JSON dumping a timedelta works as expected."""
        td = timedelta(days=1)
        self.assertEqual(json.dumps(td), '"86400.0"')

    def test_dump_decimal(self):
        """Establish that JSON dumping a decimal.Decimal object works
        as expected.
        """
        d = decimal.Decimal(1.5)
        self.assertEqual(json.dumps(d), '"1.5"')

    def test_iter(self):
        """Establish that JSON dumping an object with an __iter__ method
        works as expected.
        """
        class Foo(object):
            def __iter__(self):
                yield 4
                yield 5
                yield 6
        self.assertEqual(json.dumps(Foo()), '[4, 5, 6]')
