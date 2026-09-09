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
ScopedRateThrottle reads `view.throttle_scope` (singular), so a
viewset with multiple per-action rates would need a subclass per
action. This wrapper keeps the wiring declarative.

Rates are defined in `testimonies.settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`
under the same scope keys (`submit`, `mutation`, `audit_log`, etc.).
"""

from rest_framework.throttling import ScopedRateThrottle


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

    Reads: a `@action`-decorated method (e.g. `watchdog`) that does NOT
    appear in `throttle_scopes` falls through to the parent class's
    `get_throttle_scope`, which uses the class-level `throttle_scope`.
    To throttle a custom action, just add it to the dict — e.g.
    `{'list': 'audit_log'}` on a read-heavy viewset.
    """

    def get_throttle_scope(self, view, request):
        # `view.action` is set by DRF's initialize_request → setattr chain
        # for every dispatched action (standard CRUD + @action).
        scopes = getattr(view, 'throttle_scopes', None)
        if scopes and view.action in scopes:
            return scopes[view.action]
        return super().get_throttle_scope(view, request)
