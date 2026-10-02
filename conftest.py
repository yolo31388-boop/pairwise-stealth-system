"""Pytest configuration.

The test classes in ``tests/`` are plain classes (they do not inherit from
``unittest.TestCase``) but use ``self.assert*`` helpers. Inject the standard
``unittest.TestCase`` assertion methods into collected test classes so those
assertions work without modifying the test files.
"""

import unittest

_HELPER_NAMES = (
    "_formatMessage",
    "_truncateMessage",
    "_getAssertEqualityFunc",
    "_baseAssertEqual",
    "_diffThreshold",
)

_CLASS_ATTRS = {
    "longMessage": True,
    "maxDiff": None,
    "failureException": AssertionError,
}


def _assert_names():
    return [name for name in dir(unittest.TestCase)
            if name.startswith(("assert", "fail"))]


def pytest_collection_modifyitems(items):
    for item in items:
        cls = getattr(item, "cls", None)
        if cls is None or issubclass(cls, unittest.TestCase):
            continue
        for name in _assert_names() + list(_HELPER_NAMES):
            if not hasattr(cls, name):
                setattr(cls, name, getattr(unittest.TestCase, name))
        for attr, value in _CLASS_ATTRS.items():
            if not hasattr(cls, attr):
                setattr(cls, attr, value)
