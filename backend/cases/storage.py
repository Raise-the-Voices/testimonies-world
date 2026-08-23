"""
Storage backends for the cases app.

The default FileSystemStorage uploads everything into MEDIA_ROOT. We want
uploaded media to land in a per-visibility subdirectory
(MEDIA_ROOT/{public,restricted,sensitive}/) so that a permission-gated
download view can authoritatively decide who may fetch each file.

The routing itself is done by the ``upload_to`` callable on ``Media.file``
(see ``cases.models``); this storage backend exists so that ``MEDIA_ROOT``
is the canonical location regardless of where the upload_to callable
computes paths.
"""

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class VisibilityRouterStorage(FileSystemStorage):
    """FileSystemStorage rooted at ``settings.MEDIA_ROOT``.

    Used as the ``storage`` argument on ``Media.file`` so that all uploads
    share one filesystem root. Subdirectory placement (per-visibility) is
    controlled by the ``upload_to`` callable on the field.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('location', settings.MEDIA_ROOT)
        super().__init__(*args, **kwargs)
