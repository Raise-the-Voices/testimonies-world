from rest_framework import permissions, viewsets

from .models import Contact
from .serializers import ContactSerializer


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.prefetch_related('persons')
    serializer_class = ContactSerializer
    filterset_fields = ['role']
    search_fields = ['name', 'email', 'notes']
    permission_classes = [permissions.IsAuthenticated]
