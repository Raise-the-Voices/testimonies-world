"""Shared test base class.

All test classes across the project should inherit from `BaseTestCase`
rather than `django.test.TestCase` directly. The base ensures the
DRF throttle cache is cleared before every test, so per-action
counters don't leak between tests (the cache is process-global,
not per-test, so without this clear a high-volume test class can
429 a later class that makes 11+ writes to the same endpoint).

Why `__init_subclass__` and not a simple `setUp` override: most
of the existing 20 test classes' setUp methods don't call
`super().setUp()` — so any setUp-time work we add to
BaseTestCase gets bypassed. We can't edit 20 setUps to add
`super().setUp()` as part of a security-hardening commit
without bloating the diff and risking a regression in each
class. `__init_subclass__` lets us wrap the subclass's setUp
with a `cache.clear()` prefix at class-definition time —
zero edits to the existing test bodies, and the wrapper
runs unconditionally.

The ThrottleTests in cases/tests_security.py opt back into
genuine throttling via @override_settings and additionally
clear the cache in their own setUp so the per-test counter
is fresh; this base just keeps the OTHER tests — which assume
no throttling — from being silently broken by the new
production-rate caps.
"""

from django.core.cache import cache
from django.test import TestCase as _DjangoTestCase


def _wrap_setUp(cls):
    """Wrap `cls.setUp` to call `cache.clear()` first, then the
    original. The wrapper preserves `super().setUp()` chaining
    semantics: if the subclass's setUp doesn't call super, the
    Django parent setUp is still run by the wrapper before the
    subclass body.
    """
    original_setUp = cls.setUp

    def setUp(self):
        cache.clear()
        original_setUp(self)

    cls.setUp = setUp
    return cls


class BaseTestCase(_DjangoTestCase):
    """Test base. Every subclass gets `cache.clear()` injected
    at the start of its setUp, so throttle counters are fresh
    per test.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _wrap_setUp(cls)
