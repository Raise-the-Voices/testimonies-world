"""ViewSets for the testimonials workflow.

Mounts at `/api/testimonials/` plus transition endpoints and the
encrypted-source / precise-location reads. URL registration lives
in `testimonies/urls.py` (the project URLconf, not here).

Workflow transitions are explicit `@action` endpoints, not arbitrary
PATCH — making the side effects (audit rows, status FKs, timestamps)
forced through one well-tested path rather than scattered across
serializer field validations:

  POST /api/testimonials/{id}/submit/      draft → under_review
  POST /api/testimonials/{id}/approve/     under_review → approved
  POST /api/testimonials/{id}/reject/      under_review → rejected
  POST /api/testimonials/{id}/publish/     approved → published
  POST /api/testimonials/{id}/archive/     published → archived

The encrypted-source endpoints are routed via dedicated routes
(rather than @action) so the URL paths don't leak that a row has
sensitive data — the encryption boundary is the URL itself.
"""

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from cases.models import AuditLog, Testimonial, TestimonialTag

from .permissions import (
    CanPublishTestimonial,
    CanReviewTestimonial,
    CanSubmitTestimonial,
    CanViewEncryptedSource,
)
from .serializers import (
    TestimonialInternalSerializer,
    TestimonialPublicSerializer,
    TestimonialTagSerializer,
    TestimonialWriteSerializer,
)


class TestimonialViewSet(viewsets.ModelViewSet):
    """Read + write API for testimonials.

    Public list / detail read uses `TestimonialPublicSerializer` for
    everyone — masking is the same regardless of role on the public
    endpoint. Internal endpoints (the workflow audit info) require
    Advocate+ via the write-side permission class.

    Permissions layered per action:
      list / retrieve             public (public serializer)
      create                      CanSubmitTestimonial
      update / partial_update     CanSubmitTestimonial + owner OR Advocate
      destroy                     CanPublishTestimonial (rare — archives
                                  are preferred over deletes)
      submit                      CanSubmitTestimonial
      approve / reject            CanReviewTestimonial
      publish / archive           CanPublishTestimonial
    """

    queryset = Testimonial.objects.select_related(
        'person', 'report',
        'submitted_by', 'reviewed_by', 'approved_by', 'published_by',
    ).prefetch_related('tags')
    permission_classes = [CanSubmitTestimonial]

    def get_queryset(self):
        qs = super().get_queryset()
        # Anonymous viewers only see Published testimonials. Source /
        # location masking happens in the serializer — source_visible
        # is computed from source_visibility — so we don't filter on
        # source_visibility here.
        if not self.request.user.is_authenticated:
            return qs.filter(status=Testimonial.Status.PUBLISHED)
        return qs

    def get_serializer_class(self):
        user = self.request.user
        if self.action in ('create', 'update', 'partial_update'):
            return TestimonialWriteSerializer
        # Internal serializer for authenticated users (advocate+ audit
        # fields), public serializer for anonymous users.
        if user and user.is_authenticated:
            return TestimonialInternalSerializer
        return TestimonialPublicSerializer

    # -- Audit helpers (mirror PersonViewSet) ----------------------------

    def _client_ip(self) -> str | None:
        xff = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR')

    def _audit(self, action: str, instance: Testimonial, details: str = '') -> None:
        AuditLog.objects.create(
            user=self.request.user if self.request.user.is_authenticated else None,
            action=action,
            target_type='testimonial',
            target_id=instance.pk,
            details=details,
            ip_address=self._client_ip(),
        )

    # -- create / update ------------------------------------------------

    def perform_create(self, serializer):
        user = self.request.user
        instance = serializer.save(created_by=user)
        self._audit(AuditLog.Action.EDITED, instance, 'created')

    def perform_update(self, serializer):
        instance = serializer.save()
        self._audit(AuditLog.Action.EDITED, instance, 'updated')

    def perform_destroy(self, instance):
        # Capture provenance BEFORE delete (audit row is the only trace).
        self._audit(
            AuditLog.Action.DELETED, instance,
            f'slug={instance.slug}; status={instance.status}; '
            f'language={instance.language}',
        )
        instance.delete()

    # -- Workflow transitions -------------------------------------------

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """draft → under_review (or rejected → under_review for re-submit)."""
        return self._transition(
            request, pk,
            from_states=[Testimonial.Status.DRAFT,
                         Testimonial.Status.REJECTED],
            to_state=Testimonial.Status.UNDER_REVIEW,
            action_name='submit',
        )

    @action(
        detail=True, methods=['post'],
        permission_classes=[CanReviewTestimonial],
    )
    def approve(self, request, pk=None):
        """under_review → approved. Notes optional in body."""
        notes = (request.data.get('review_notes') or '').strip()
        return self._transition(
            request, pk,
            from_states=[Testimonial.Status.UNDER_REVIEW],
            to_state=Testimonial.Status.APPROVED,
            action_name='approve',
            extra_fields={'review_notes': notes, 'reviewed_by': request.user,
                          'reviewed_at': timezone.now()},
        )

    @action(
        detail=True, methods=['post'],
        permission_classes=[CanReviewTestimonial],
    )
    def reject(self, request, pk=None):
        """under_review → rejected. Notes required (reason)."""
        notes = (request.data.get('review_notes') or '').strip()
        if not notes:
            raise ValidationError({
                'review_notes': 'A reason is required when rejecting.',
            })
        return self._transition(
            request, pk,
            from_states=[Testimonial.Status.UNDER_REVIEW],
            to_state=Testimonial.Status.REJECTED,
            action_name='reject',
            extra_fields={'review_notes': notes, 'reviewed_by': request.user,
                          'reviewed_at': timezone.now()},
        )

    @action(
        detail=True, methods=['post'],
        permission_classes=[CanPublishTestimonial],
    )
    def publish(self, request, pk=None):
        """approved → published. Sets published_by / published_at."""
        return self._transition(
            request, pk,
            from_states=[Testimonial.Status.APPROVED],
            to_state=Testimonial.Status.PUBLISHED,
            action_name='publish',
            extra_fields={'published_by': request.user,
                          'published_at': timezone.now()},
        )

    @action(
        detail=True, methods=['post'],
        permission_classes=[CanPublishTestimonial],
    )
    def archive(self, request, pk=None):
        """published → archived. Soft-delete (row stays)."""
        return self._transition(
            request, pk,
            from_states=[Testimonial.Status.PUBLISHED],
            to_state=Testimonial.Status.ARCHIVED,
            action_name='archive',
            extra_fields={'archived_at': timezone.now()},
        )

    def _transition(self, request, pk, *, from_states, to_state,
                    action_name, extra_fields=None):
        """Shared transition runner — enforces state machine + audit row.

        Returns the updated row via the InternalSerializer so the
        client sees the new status without an extra GET.
        """
        instance = self.get_object()
        if instance.status not in from_states:
            raise ValidationError({
                'status': f'Cannot {action_name} from '
                          f'"{instance.status}". Allowed: '
                          f'{", ".join(from_states)}.',
            })

        previous = instance.status
        instance.status = to_state
        for field, value in (extra_fields or {}).items():
            setattr(instance, field, value)
        # When transitioning into a reviewable state, stamp submitted_by
        # for the DRAFT→UNDER_REVIEW path. (approve/reject set
        # reviewed_by via extra_fields.)
        if action_name == 'submit':
            instance.submitted_by = request.user
            instance.submitted_at = timezone.now()
        instance.save()

        self._audit(
            AuditLog.Action.EDITED, instance,
            f'transition {previous} → {to_state} '
            f'(action={action_name})',
        )

        return Response(
            TestimonialInternalSerializer(instance).data,
            status=status.HTTP_200_OK,
        )

    # -- Encrypted-source endpoints (CanViewEncryptedSource only) ---------
    # These are deliberately routed separately (not exposed via the
    # public serializer) so the URL itself is the security boundary —
    # a volunteer pulling /api/testimonials/42/ never even sees the
    # encrypted columns exist. Only Advocate / Admin requesters can
    # hit these endpoints, and each hit writes an AuditLog row.

    @action(
        detail=True, methods=['get'],
        permission_classes=[CanViewEncryptedSource],
    )
    def source(self, request, pk=None):
        """Decrypt and return the real source identity.

        Audit-logged on read — even Advocate+ accesses leave a trace
        because the real source identity is the most sensitive datum
        on this row.
        """
        instance = self.get_object()
        # Plaintext could be None if the row was created without a
        # source (source_encrypted is nullable); distinguish that
        # from ciphertext unavailability by always reporting the
        # visibility label too.
        plaintext = instance.get_source()
        self._audit(
            AuditLog.Action.VIEWED, instance,
            f'decrypted source (visibility={instance.source_visibility})',
        )
        return Response({
            'id': instance.id,
            'source_visibility': instance.source_visibility,
            'public_source_label': instance.public_source_label,
            'source': plaintext,
        })

    @action(
        detail=True, methods=['get'],
        permission_classes=[CanViewEncryptedSource],
    )
    def precise_location(self, request, pk=None):
        """Decrypt and return the precise-location ciphertext.

        Same audit-on-read posture as the source endpoint.
        """
        instance = self.get_object()
        plaintext = instance.get_precise_location()
        self._audit(
            AuditLog.Action.VIEWED, instance,
            f'decrypted precise location (visibility={instance.location_visibility})',
        )
        return Response({
            'id': instance.id,
            'location_visibility': instance.location_visibility,
            'public_location_display': instance.public_location_display,
            'precise_location': plaintext,
        })


class TestimonialTagViewSet(viewsets.ModelViewSet):
    """Lookup-table CRUD for testimonial tags.

    Read-open to anyone (tags are public taxonomy); writes require
    Advocate or staff (mass-assignment guard per SYSTEM_RULES §5 —
    `is_published`-style gates don't apply here but the principle of
    \"server controls metadata\" does, and creating a tag shouldn't be
    free for any random authenticated user).
    """

    queryset = TestimonialTag.objects.all().order_by('name')
    serializer_class = TestimonialTagSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,
                          CanPublishTestimonial]
