"""Testimonials module — publication-facing wrapper around cases.

Imports stay intentionally light here; concrete helpers live in
encryption.py / permissions.py / serializers.py / views.py / tests.py.
The package is mounted on the existing `cases` app per project
convention (one Django app per project, not one per module).
"""
