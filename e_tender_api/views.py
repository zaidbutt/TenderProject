from django.http.response import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework import filters
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from e_tender_api import serializers, models, permissions
from django.contrib.auth import authenticate, login, logout
from rest_framework.authtoken.models import Token
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from .tokens import account_activation_token
from django.core.mail import send_mail
import json


class Register(APIView):
    serializer_class = serializers.UserProfileSerializer
    permission_classes = [AllowAny]

    
    def post(self, request):
        email = request.data["email"]
        organization_name = request.data["organization_name"]
        password= request.data["password"]
        ntn = request.data["ntn"]
        address = request.data["address"]
        contact = request.data["contact"]
        if models.UserProfile.objects.filter(email=email).exists():
            return Response({"Error":"Email exists"})
        user =models.UserProfile.objects.create_user(organization_name=organization_name
                                                    , password=password, email=email,
                                                      ntn = ntn, address=address, contact = contact)

        user.is_active = False
        user.save()
            
        mail_subject = 'Activate your account.'
        
        message = {
                            'user': user.ntn,
                            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                            'token': account_activation_token.make_token(user),
                        }
        to_email = email
            
        send_mail(mail_subject, json.dumps(message), "fa17-bcs-081@cuilahore.edu.pk", [to_email])
            
            
        return HttpResponse('Please confirm your email address to complete the registration')                                              
                                            





class UserProfileViewSet(viewsets.ModelViewSet):
    """handle creating and updating profiles"""
    serializer_class = serializers.UserProfileSerializer
    queryset = models.UserProfile.objects.all()
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.UpdateOwnProfile,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('organization_name', 'email',)



    def destroy(self, request):
        """Handle removing an object"""
        return Response({'http_method': 'DELETE'})


class TenderViewSet(viewsets.ModelViewSet):
    """handle creating tender"""
    serializer_class = serializers.PublishTenderSerializer
    queryset = models.Tenders.objects.all()
    filter_backends = (filters.SearchFilter,)
    search_fields = ('category', 'region')

# add search fields by keywords category etc


class BidViewSet(viewsets.ModelViewSet):
    """handle creating tender"""
    serializer_class = serializers.PostBidSerializer
    queryset = models.Bid.objects.all()
    filter_backends = (filters.SearchFilter,)
    search_fields = ('bidding_amount', 'tenderId')

    def patch(self, request, pk=None):
        """Handle updating part of an object"""
        return Response({'http_method': 'PATCH'})


class UserLoginApiView(ObtainAuthToken):
    """Handle creating user authentication tokens"""
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)        
        user = serializer.validated_data['user']
        print(user)
        if user.is_active:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'organization': user.organization_name,
                'email': user.email
            })
        return Response({"Please Activate Your Account"})

@csrf_exempt
def activate(request):
    token = request.POST["token"]
    try:
        uid = force_text(urlsafe_base64_decode(request.POST["uid"]))
        user = models.UserProfile.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return HttpResponse('Thank you for your email confirmation. Now you can login your account.')
    else:
        return HttpResponse('Activation link is invalid!')