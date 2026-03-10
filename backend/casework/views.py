from rest_framework import permissions, viewsets

from .models import CaseworkRecord
from .serializers import CaseworkRecordSerializer


class CaseworkRecordViewSet(viewsets.ModelViewSet):
    serializer_class = CaseworkRecordSerializer
    filterset_fields = ['action_type', 'status', 'performed_by']
    search_fields = ['description', 'notes', 'next_steps']
    ordering_fields = ['date', 'created_at', 'status']
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CaseworkRecord.objects.prefetch_related('persons').select_related('performed_by')

    def perform_create(self, serializer):
        serializer.save(performed_by=self.request.user)
