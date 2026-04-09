# applications/views.py
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Application, Document
from rest_framework import status, generics, permissions
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from .serializers import (
    ApplicationCreateSerializer,
    ApplicationListSerializer,
    ApplicationDetailSerializer,
    DocumentSerializer,
)
from packages.models import Package


class ApplicationListView(generics.ListAPIView):
    serializer_class = ApplicationListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Application.objects.filter(
            user=self.request.user
        ).select_related('package').prefetch_related('documents')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'applications': serializer.data,
            'count': queryset.count(),
            'message': 'Applications retrieved successfully!'
        }, status=status.HTTP_200_OK)


class ApplicationCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        package_id = request.data.get('package')
        if not package_id:
            return Response({'error': 'package is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            Package.objects.get(id=package_id, is_active=True)
        except Package.DoesNotExist:
            return Response({'error': 'Package not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ApplicationCreateSerializer(data=request.data)
        if serializer.is_valid():
            application = serializer.save(user=request.user)
            detail_serializer = ApplicationDetailSerializer(application)
            return Response({
                'application': detail_serializer.data,
                'message': 'Application created successfully! Click Start Application to begin.'
            }, status=status.HTTP_201_CREATED)

        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ApplicationDetailView(generics.RetrieveAPIView):
    serializer_class = ApplicationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        is_agent = hasattr(user, 'agent_profile')
        
        if is_agent:
            return Application.objects.all().select_related('package', 'user').prefetch_related('documents')
        
        return Application.objects.filter(
            user=user
        ).select_related('package', 'user').prefetch_related('documents')

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response({
                'application': serializer.data,
                'message': 'Application details retrieved successfully!'
            }, status=status.HTTP_200_OK)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

class ApplicationStartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        try:
            application = Application.objects.get(id=id, user=request.user)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

        if application.status != 'not_started':
            return Response({
                'error': 'Application has already been started'
            }, status=status.HTTP_400_BAD_REQUEST)

        application.status = 'started'
        application.consultant_name = 'Sarah Mitchell'
        application.consultant_title = 'Visa Consultant'
        application.meeting_date = request.data.get('meeting_date', None)
        application.meeting_time = request.data.get('meeting_time', '10:00 AM - 10:30 AM')
        application.meeting_status = 'scheduled'
        application.save()

        serializer = ApplicationDetailSerializer(application)
        return Response({
            'application': serializer.data,
            'message': 'Application started! Your consultant has been assigned and a discovery meeting has been scheduled.'
        }, status=status.HTTP_200_OK)

        
class MeetingCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, id):
        try:
            application = Application.objects.get(id=id, user=request.user)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

        if not application.can_cancel_meeting:
            return Response({
                'error': 'You have used all 3 cancellations and can no longer cancel this meeting.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if application.meeting_status == 'completed':
            return Response({
                'error': 'This meeting has already been completed and cannot be cancelled.'
            }, status=status.HTTP_400_BAD_REQUEST)

        application.meeting_status = 'cancelled'
        application.cancellations_used += 1
        application.save()

        serializer = ApplicationDetailSerializer(application)
        return Response({
            'application': serializer.data,
            'cancellations_left': application.cancellations_left,
            'message': f'Meeting cancelled. You have {application.cancellations_left} cancellation(s) remaining.'
        }, status=status.HTTP_200_OK)


class MeetingCompleteView(APIView):
    """
    PATCH /api/applications/<id>/meeting/complete/
    ✅ Changed from IsAdminUser to IsAuthenticated so agents can call it.
    """
    permission_classes = [permissions.IsAuthenticated]  # ✅ was IsAdminUser

    def patch(self, request, id):
        try:
            application = Application.objects.get(id=id)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

        if application.meeting_status == 'completed':
            return Response({
                'error': 'Meeting is already marked as completed.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if application.status == 'not_started':
            return Response({
                'error': 'Application has not been started yet.'
            }, status=status.HTTP_400_BAD_REQUEST)

        application.meeting_status = 'completed'
        application.status = 'processing'
        application.save()

        serializer = ApplicationDetailSerializer(application)
        return Response({
            'application': serializer.data,
            'message': 'Discovery call completed! Chat is now unlocked for the client.'
        }, status=status.HTTP_200_OK)


class DocumentUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, id):
        try:
            application = Application.objects.get(id=id, user=request.user)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(application=application)
            return Response({
                'document': serializer.data,
                'message': 'Document uploaded successfully!'
            }, status=status.HTTP_201_CREATED)

        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class DocumentDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, id, doc_id):
        try:
            application = Application.objects.get(id=id, user=request.user)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            document = Document.objects.get(id=doc_id, application=application)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)

        document.file.delete(save=False)
        document.delete()

        return Response({'message': 'Document deleted successfully!'}, status=status.HTTP_200_OK)


class ApplicationDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, id):
        try:
            application = Application.objects.get(id=id, user=request.user)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

        if application.status != 'not_started':
            return Response({
                'error': f'Cannot delete application with status: {application.get_status_display()}'
            }, status=status.HTTP_400_BAD_REQUEST)

        application.delete()
        return Response({'message': 'Application deleted successfully!'}, status=status.HTTP_200_OK)


class AdminApplicationListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        applications = Application.objects.all().select_related('package', 'user')
        serializer = ApplicationListSerializer(applications, many=True)
        return Response({
            'applications': serializer.data,
        }, status=status.HTTP_200_OK)


class ApplicationMessagesView(APIView):
    """
    GET  /api/applications/<id>/messages/  — fetch chat history
    POST /api/applications/<id>/messages/  — send a text message
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        from .models import Application, ApplicationMessage
        try:
            # Clients can only see their own; agents can see any
            application = Application.objects.get(id=id)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found.'}, status=404)

        # Permission check — client can only read their own
        is_agent = hasattr(request.user, 'agent_profile')
        if not is_agent and application.user != request.user:
            return Response({'error': 'Forbidden.'}, status=403)

        messages = ApplicationMessage.objects.filter(
            application=application
        ).select_related('sender').order_by('created_at')

        data = [
            {
                'id':           str(msg.id),
                'content':      msg.content,
                'sender_role':  msg.sender_role,
                'sender_id':    str(msg.sender_id),
                'sender_name':  (
                    msg.sender.get_full_name() or msg.sender.email
                    if msg.sender else 'Unknown'
                ),
                'message_type': msg.message_type,
                'file_url':     request.build_absolute_uri(msg.file_url.url) if msg.file_url else None,
                'file_name':    msg.file_name,
                'created_at':   msg.created_at.isoformat(),
            }
            for msg in messages
        ]
        return Response({'messages': data})

    def post(self, request, id):
        from .models import Application, ApplicationMessage
        try:
            application = Application.objects.get(id=id)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found.'}, status=404)

        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': 'Message content is required.'}, status=400)

        # Determine sender role
        is_agent = hasattr(request.user, 'agent_profile')
        sender_role = 'consultant' if is_agent else 'client'

        # Block clients from chatting if meeting not completed
        if not is_agent and application.meeting_status != 'completed':
            return Response(
                {'error': 'Chat is locked until your discovery meeting is completed.'},
                status=403
            )

        msg = ApplicationMessage.objects.create(
            application=application,
            sender=request.user,
            sender_role=sender_role,
            content=content,
            message_type='text',
        )

        return Response({
            'id':           str(msg.id),
            'content':      msg.content,
            'sender_role':  msg.sender_role,
            'sender_id':    str(msg.sender_id),
            'message_type': 'text',
            'created_at':   msg.created_at.isoformat(),
        }, status=201)


class ApplicationMessageFileView(APIView):
    """
    POST /api/applications/<id>/messages/file/  — send a file/document
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        from .models import Application, ApplicationMessage
        try:
            application = Application.objects.get(id=id)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found.'}, status=404)

        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided.'}, status=400)

        is_agent = hasattr(request.user, 'agent_profile')
        sender_role = 'consultant' if is_agent else 'client'

        if not is_agent and application.meeting_status != 'completed':
            return Response(
                {'error': 'Chat is locked until your discovery meeting is completed.'},
                status=403
            )

        msg = ApplicationMessage.objects.create(
            application=application,
            sender=request.user,
            sender_role=sender_role,
            content='',
            message_type='file',
            file_url=file,
            file_name=file.name,
        )

        return Response({
            'id':           str(msg.id),
            'sender_role':  msg.sender_role,
            'message_type': 'file',
            'file_url':     request.build_absolute_uri(msg.file_url.url),
            'file_name':    msg.file_name,
            'created_at':   msg.created_at.isoformat(),
        }, status=201)
