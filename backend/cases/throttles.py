"""DRF throttle classes for the cases app.

We extend `ScopedRateThrottle` to resolve the scope from a per-viewset
dict of action→scope mappings. That lets each ViewSet declare e.g.

    throttle_scopes = {
        'create':  'submit',
        'update':  'mutation',
        'destroy': 'mutation',
    }

without subclassing per action. If the current action isn't in the
dict, we fall back to the class-level `throttle_scope` (DRF default).

Why custom and not just configure ScopedRateThrottle: the out-of-the-box
ScopedRateThrottle reads `view.throttle_scope` (singular) inside
`allow_request`, so a viewset with multiple per-action rates would
need a subclass per action. This wrapper keeps the wiring declarative.

Rates are defined in `testimonies.settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`
under the same scope keys (`submit`, `mutation`, `audit_log`, etc.).

Implementation note: we override `get_rate` to read from
`api_settings.DEFAULT_THROTTLE_RATES` live rather than the class
attribute `THROTTLE_RATES` (which DRF sets at class-definition time
and never updates). Reading live means `@override_settings` in tests
works correctly — without this, the throttle always uses the
production rate and tests can't shrink the cap.
"""

from rest_framework.settings import api_settings
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


class ActionScopedThrottle(ScopedRateThrottle):
    """Per-action throttle scope resolver.

    Usage on a viewset:

        class PersonViewSet(viewsets.ModelViewSet):
            throttle_classes = [ActionScopedThrottle]
            throttle_scopes = {
                'create': 'submit',
                'update': 'mutation',
                'partial_update': 'mutation',
                'destroy': 'mutation',
            }

    A `@action`-decorated method (e.g. `watchdog`) that does NOT
    appear in `throttle_scopes` falls through to the parent class's
    `allow_request`, which uses the class-level `throttle_scope`.
    To throttle a custom action, just add it to the dict — e.g.
    `{'list': 'audit_log'}` on a read-heavy viewset.
    """

    scope_attr = 'throttle_scope'

    def get_rate(self):
        """Read the rate live from api_settings.

        Overrides `SimpleRateThrottle.get_rate`, which reads
        `self.THROTTLE_RATES[self.scope]` — a class attribute that
        DRF sets at class-definition time and never updates. Without
        this override, `@override_settings(REST_FRAMEWORK=...)` in
        tests is silently ignored and the throttle always uses the
        production rate.
        """
        if not getattr(self, 'scope', None):
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                f"You must set `.scope` on {self.__class__.__name__} "
                "before calling get_rate()."
            )
        try:
            # Re-read every call so override_settings in tests works.
            rates = api_settings.DEFAULT_THROTTLE_RATES or {}
            return rates[self.scope]
        except KeyError:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                f"No default throttle rate set for '{self.scope}' scope. "
                "Add it to REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] in settings."
            )

    def _resolve_scope(self, view, request):
        """Pick the scope string for this request.

        Priority:
          1. `view.throttle_scopes[view.action]` if defined — the
             per-action dict.
          2. `getattr(view, 'throttle_scope', None)` — DRF's
             class-level fallback (singular).
          3. None — parent class treats None as "no throttle".
        """
        scopes = getattr(view, 'throttle_scopes', None)
        if scopes and getattr(view, 'action', None) in scopes:
            return scopes[view.action]
        return getattr(view, self.scope_attr, None)

    def allow_request(self, request, view):
        """Override ScopedRateThrottle.allow_request to use our scope
        resolver and our get_rate() override.

        Implementation note: we override `allow_request` (not
        `get_throttle_scope`) because ScopedRateThrottle's
        `allow_request` reads `self.scope = getattr(view, 'throttle_scope', ...)`
        directly — it does NOT call `get_throttle_scope()` at all.
        The DRF docstring suggests otherwise; the source confirms.

        We call `SimpleRateThrottle.allow_request` directly, NOT
        `super().allow_request()`. The super chain here is
        SimpleRateThrottle → ScopedRateThrottle → ActionScopedThrottle,
        so `super()` resolves to `ScopedRateThrottle.allow_request`,
        which would overwrite our `self.scope` with
        `getattr(view, 'throttle_scope', None)` (= None, because
        viewsets only declare `throttle_scopes`). Calling
        `SimpleRateThrottle.allow_request` skips that re-assignment.
        """
        self.scope = self._resolve_scope(view, request)
        if not self.scope:
            return True
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return SimpleRateThrottle.allow_request(self, request, view)
