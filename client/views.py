# client/views.py - Endpoints principales
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, Follow, Post, Message, PostLike, MessageLike, Notification
from .serializers import (
    UserSerializer, UserRegisterSerializer, UserUpdateSerializer,
    PostSerializer, PostCreateSerializer, PostUpdateSerializer,
    MessageSerializer, MessageCreateSerializer, MessageUpdateSerializer,
    FollowSerializer, NotificationSerializer
)


# ==================== AUTH VIEWS ====================
# class RegisterView(generics.CreateAPIView):
#     queryset = User.objects.all()
#     serializer_class = UserRegisterSerializer
#     permission_classes = [permissions.AllowAny]


# class LoginView(APIView):
#     permission_classes = [permissions.AllowAny]
    
#     def post(self, request):
#         username = request.data.get('username')
#         password = request.data.get('password')
#         user = authenticate(username=username, password=password)
        
#         if user:
#             refresh = RefreshToken.for_user(user)
#             return Response({
#                 'access': str(refresh.access_token),
#                 'refresh': str(refresh),
#                 'user': UserSerializer(user, context={'request': request}).data
#             })
#         return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)


from .utils import send_verification_email, verify_email, resend_verification_email

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def perform_create(self, serializer):
        user = serializer.save()
        # Enviar email de verificación
        send_verification_email(user, self.request)
        return user


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        
        if user:
            # Verificar si el email está verificado
            if not user.email_verified:
                return Response(
                    {'error': 'email_not_verified', 'message': 'Debes verificar tu cuenta antes de iniciar sesión. Revisa tu correo.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user, context={'request': request}).data
            })
        return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)


class VerifyEmailView(APIView):
    """Verificar email con token"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        success, user = verify_email(token)
        
        if success:
            return Response({
                'success': True,
                'message': 'Email verificado correctamente. Ya puedes iniciar sesión.'
            })
        elif user:
            return Response({
                'success': False,
                'message': 'Este email ya está verificado'
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'success': False,
                'message': 'Token inválido o expirado'
            }, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationEmailView(APIView):
    """Reenviar email de verificación - puede ser usado sin autenticación"""
    permission_classes = [permissions.AllowAny]  # Cambiar a AllowAny
    
    def post(self, request):
        # Obtener email o username del request
        email = request.data.get('email')
        username = request.data.get('username')
        
        # Buscar usuario por email o username
        user = None
        if email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                pass
        
        if not user and username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                pass
        
        if not user:
            return Response({
                'success': False,
                'message': 'No se encontró un usuario con esos datos'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verificar si ya está verificado
        if user.email_verified:
            return Response({
                'success': False,
                'message': 'Tu cuenta ya está verificada'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Reenviar email de verificación
        from .utils import send_verification_email
        success = send_verification_email(user, request)
        
        if success:
            return Response({
                'success': True,
                'message': 'Email de verificación reenviado. Revisa tu bandeja de entrada.'
            })
        else:
            return Response({
                'success': False,
                'message': 'Error al enviar el email. Intenta nuevamente.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from .utils import send_password_reset_email, validate_password_reset_token, reset_password


class PasswordResetRequestView(APIView):
    """Solicitar recuperación de contraseña"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response(
                {'error': 'El correo electrónico es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = send_password_reset_email(email, request)
        
        if success:
            return Response({
                'success': True,
                'message': 'Si el correo está registrado, recibirás instrucciones para restablecer tu contraseña.'
            })
        else:
            return Response({
                'success': False,
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetValidateView(APIView):
    """Validar token de recuperación"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response(
                {'error': 'Token requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid, user, error = validate_password_reset_token(token)
        
        if valid:
            return Response({
                'success': True,
                'message': 'Token válido',
                'email': user.email
            })
        else:
            return Response({
                'success': False,
                'message': error
            }, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """Confirmar nueva contraseña"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        if not token:
            return Response(
                {'error': 'Token requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not new_password or not confirm_password:
            return Response(
                {'error': 'La nueva contraseña es requerida'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_password != confirm_password:
            return Response(
                {'error': 'Las contraseñas no coinciden'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_password) < 6:
            return Response(
                {'error': 'La contraseña debe tener al menos 6 caracteres'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = reset_password(token, new_password)
        
        if success:
            return Response({
                'success': True,
                'message': message
            })
        else:
            return Response({
                'success': False,
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)





class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer
    
    def get_object(self):
        return self.request.user


class PublicProfileView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'


# ==================== POST VIEWS (PRODUCTOS) ====================
class PostListCreateView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        posts = Post.objects.filter(is_active=True, is_sold=False).order_by('-created_at')
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Debes iniciar sesión para publicar'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not request.user.is_store_active:
            return Response({'error': 'Debes activar tu tienda primero'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = PostCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            post = serializer.save()
            
            for follower in request.user.followers.all():
                Notification.objects.create(
                    user=follower.follower,
                    type=Notification.Type.NEW_POST,
                    actor=request.user,
                    post=post
                )
            
            output_serializer = PostSerializer(post, context={'request': request})
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyPostsView(generics.ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Post.objects.filter(seller=self.request.user).order_by('-created_at')


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PostUpdateSerializer
        return PostSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context
    
    def perform_update(self, serializer):
        if self.get_object().seller != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permiso para editar esta publicación")
        serializer.save()
    
    def perform_destroy(self, instance):
        if instance.seller != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permiso para eliminar esta publicación")
        instance.delete()


class SellerPostsView(generics.ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        seller_id = self.kwargs['seller_id']
        return Post.objects.filter(seller_id=seller_id, is_active=True).order_by('-created_at')


class PostLikeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, post_id):
        post = Post.objects.get(id=post_id)
        like, created = PostLike.objects.get_or_create(user=request.user, post=post)
        
        if created:
            post.likes_count += 1
            post.save()
            
            if post.seller != request.user:
                Notification.objects.create(
                    user=post.seller,
                    type=Notification.Type.LIKE_POST,
                    actor=request.user,
                    post=post
                )
            
            return Response({'status': 'liked'}, status=status.HTTP_201_CREATED)
        else:
            like.delete()
            post.likes_count -= 1
            post.save()
            return Response({'status': 'unliked'}, status=status.HTTP_200_OK)


# ==================== MESSAGE VIEWS ====================
class MessageListCreateView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        messages = Message.objects.filter(is_active=True).order_by('-created_at')
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Debes iniciar sesión para publicar'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not request.user.is_store_active:
            return Response({'error': 'Debes activar tu tienda primero'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = MessageCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            message = serializer.save()
            
            for follower in request.user.followers.all():
                Notification.objects.create(
                    user=follower.follower,
                    type=Notification.Type.NEW_MESSAGE,
                    actor=request.user,
                    message=message
                )
            
            output_serializer = MessageSerializer(message, context={'request': request})
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyMessagesView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Message.objects.filter(seller=self.request.user).order_by('-created_at')


class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Message.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return MessageUpdateSerializer
        return MessageSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context
    
    def perform_update(self, serializer):
        if self.get_object().seller != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permiso para editar este mensaje")
        serializer.save()
    
    def perform_destroy(self, instance):
        if instance.seller != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permiso para eliminar este mensaje")
        instance.delete()


class SellerMessagesView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        seller_id = self.kwargs['seller_id']
        return Message.objects.filter(seller_id=seller_id, is_active=True).order_by('-created_at')


class MessageLikeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, message_id):
        message = Message.objects.get(id=message_id)
        like, created = MessageLike.objects.get_or_create(user=request.user, message=message)
        
        if created:
            message.likes_count += 1
            message.save()
            
            if message.seller != request.user:
                Notification.objects.create(
                    user=message.seller,
                    type=Notification.Type.LIKE_MESSAGE,
                    actor=request.user,
                    message=message
                )
            
            return Response({'status': 'liked'}, status=status.HTTP_201_CREATED)
        else:
            like.delete()
            message.likes_count -= 1
            message.save()
            return Response({'status': 'unliked'}, status=status.HTTP_200_OK)


# ==================== FOLLOW VIEWS ====================
class FollowView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, user_id):
        following = User.objects.get(id=user_id)
        
        if following == request.user:
            return Response({'error': 'No puedes seguirte a ti mismo'}, status=status.HTTP_400_BAD_REQUEST)
        
        follow, created = Follow.objects.get_or_create(follower=request.user, following=following)
        
        if created:
            request.user.following_count += 1
            request.user.save()
            following.followers_count += 1
            following.save()
            
            Notification.objects.create(
                user=following,
                type=Notification.Type.FOLLOW,
                actor=request.user
            )
            
            return Response({'status': 'followed'}, status=status.HTTP_201_CREATED)
        else:
            follow.delete()
            request.user.following_count -= 1
            request.user.save()
            following.followers_count -= 1
            following.save()
            return Response({'status': 'unfollowed'}, status=status.HTTP_200_OK)


class FollowersView(generics.ListAPIView):
    serializer_class = FollowSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return Follow.objects.filter(following_id=user_id)


class FollowingView(generics.ListAPIView):
    serializer_class = FollowSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return Follow.objects.filter(follower_id=user_id)


# ==================== FEED VIEWS ====================
class FeedView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        if request.user.is_authenticated:
            following_users = request.user.following.values_list('following_id', flat=True)
            
            posts = Post.objects.filter(
                seller_id__in=following_users, 
                is_active=True, 
                is_sold=False
            ).order_by('-created_at')
            
            messages = Message.objects.filter(
                seller_id__in=following_users,
                is_active=True
            ).order_by('-created_at')
        else:
            posts = Post.objects.filter(is_active=True, is_sold=False).order_by('-created_at')[:20]
            messages = Message.objects.filter(is_active=True).order_by('-created_at')[:20]
        
        post_serializer = PostSerializer(posts, many=True, context={'request': request})
        message_serializer = MessageSerializer(messages, many=True, context={'request': request})
        
        combined = list(post_serializer.data) + list(message_serializer.data)
        combined.sort(key=lambda x: x['created_at'], reverse=True)
        
        return Response(combined)


# ==================== NOTIFICATION VIEWS ====================
class NotificationsView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MarkNotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, notification_id):
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            return Response({'status': 'marked as read'})
        except Notification.DoesNotExist:
            return Response({'error': 'Notificación no encontrada'}, status=status.HTTP_404_NOT_FOUND)


class MarkAllNotificationsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'all marked as read'})


class NotificationDeleteView(generics.DestroyAPIView):
    """Eliminar una notificación específica"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        instance.delete()


class DeleteAllNotificationsView(APIView):
    """Eliminar todas las notificaciones del usuario"""
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request):
        Notification.objects.filter(user=request.user).delete()
        return Response({'status': 'all notifications deleted'})



class ExploreContentView(generics.ListAPIView):
    """Explorar contenido (productos y mensajes)"""
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        content_type = self.request.query_params.get('type', 'all')
        search = self.request.query_params.get('q', '')
        category = self.request.query_params.get('category', '')
        price_min = self.request.query_params.get('price_min')
        price_max = self.request.query_params.get('price_max')
        
        results = []
        
        # Productos
        if content_type in ['all', 'products']:
            products = Post.objects.filter(is_active=True, is_sold=False)
            if search:
                products = products.filter(description__icontains=search)
            if category:
                products = products.filter(category=category)
            if price_min:
                products = products.filter(price__gte=price_min)
            if price_max:
                products = products.filter(price__lte=price_max)
            results.extend(products)
        
        # Mensajes
        if content_type in ['all', 'messages']:
            messages = Message.objects.filter(is_active=True)
            if search:
                messages = messages.filter(content__icontains=search)
            results.extend(messages)
        
        # Ordenar por fecha
        results.sort(key=lambda x: x.created_at, reverse=True)
        
        # Paginación
        page = int(self.request.query_params.get('page', 1))
        page_size = 20
        start = (page - 1) * page_size
        end = start + page_size
        
        return results[start:end]
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Serializar según tipo
        serialized = []
        for item in queryset:
            if isinstance(item, Post):
                serialized.append(PostSerializer(item, context={'request': request}).data)
            else:
                serialized.append(MessageSerializer(item, context={'request': request}).data)
        
        return Response({
            'results': serialized,
            'count': len(serialized),
            'next': None
        })


class ExploreSellersView(generics.ListAPIView):
    """Explorar vendedores"""
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        search = self.request.query_params.get('q', '')
        category = self.request.query_params.get('category', '')
        
        queryset = User.objects.filter(is_store_active=True, is_active=True)
        
        if search:
            queryset = queryset.filter(
                Q(store_name__icontains=search) |
                Q(username__icontains=search) |
                Q(store_description__icontains=search)
            )
        
        if category:
            queryset = queryset.filter(posts__category=category).distinct()
        
        return queryset.order_by('-followers_count')[:20]




# client/views.py - Agregar vistas de admin

from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import User, Post, Message, Follow
from .serializers import UserSerializer, PostSerializer, MessageSerializer

class IsAdminUser(permissions.BasePermission):
    """Permiso solo para usuarios administradores"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class AdminDashboardView(APIView):
    """Vista de estadísticas para el dashboard admin"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        # Estadísticas generales
        stats = {
            'users': User.objects.count(),
            'stores': User.objects.filter(is_store_active=True).count(),
            'products': Post.objects.filter(is_active=True).count(),
            'messages': Message.objects.filter(is_active=True).count(),
        }
        
        # Usuarios recientes (últimos 7 días)
        week_ago = timezone.now() - timedelta(days=7)
        recent_users = User.objects.filter(created_at__gte=week_ago).order_by('-created_at')[:10]
        
        # Productos más populares
        top_products = Post.objects.filter(is_active=True).order_by('-likes_count')[:10]
        
        # Actividad por día (últimos 7 días)
        activity = []
        for i in range(6, -1, -1):
            day = timezone.now() - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0)
            day_end = day.replace(hour=23, minute=59, second=59)
            
            activity.append({
                'date': day.strftime('%d/%m'),
                'users': User.objects.filter(created_at__range=(day_start, day_end)).count(),
                'products': Post.objects.filter(created_at__range=(day_start, day_end)).count(),
                'messages': Message.objects.filter(created_at__range=(day_start, day_end)).count(),
            })
        
        activity_data = {
            'labels': [a['date'] for a in activity],
            'users': [a['users'] for a in activity],
            'products': [a['products'] for a in activity],
            'messages': [a['messages'] for a in activity],
        }
        
        return Response({
            'stats': stats,
            'recent_users': UserSerializer(recent_users, many=True, context={'request': request}).data,
            'top_products': PostSerializer(top_products, many=True, context={'request': request}).data,
            'activity': activity_data,
        })


class AdminUserListView(generics.ListAPIView):
    """Listar todos los usuarios (admin)"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        return User.objects.all().order_by('-created_at')


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    """Detalle y edición de usuario (admin)"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    queryset = User.objects.all()
    lookup_field = 'id'
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Campos que se pueden actualizar
        allowed_fields = ['rank', 'max_products', 'max_messages', 'store_name', 'email', 'first_name', 'last_name', 'phone', 'website', 'bio']
        
        # Actualizar solo los campos que vienen en la request
        for field in allowed_fields:
            if field in request.data:
                value = request.data[field]
                # Convertir a número si es necesario
                if field in ['max_products', 'max_messages']:
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        continue
                setattr(instance, field, value)
        
        instance.save()
        
        # Devolver el usuario actualizado
        serializer = UserSerializer(instance, context={'request': request})
        return Response(serializer.data)




class AdminUserToggleStaffView(APIView):
    """Activar/desactivar permisos de administrador"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def post(self, request, user_id):
        user = User.objects.get(id=user_id)
        user.is_staff = not user.is_staff
        user.save()
        return Response({'status': 'toggled', 'is_staff': user.is_staff})


class AdminUserToggleActiveView(APIView):
    """Activar/desactivar usuario"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def post(self, request, user_id):
        user = User.objects.get(id=user_id)
        user.is_active = not user.is_active
        user.save()
        return Response({'status': 'toggled', 'is_active': user.is_active})


class AdminPostListView(generics.ListAPIView):
    """Listar todos los productos (admin)"""
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        return Post.objects.all().order_by('-created_at')


class AdminPostDeleteView(generics.DestroyAPIView):
    """Eliminar producto (admin)"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    queryset = Post.objects.all()
    lookup_field = 'id'


class AdminMessageListView(generics.ListAPIView):
    """Listar todos los mensajes (admin)"""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        return Message.objects.all().order_by('-created_at')


class AdminMessageDeleteView(generics.DestroyAPIView):
    """Eliminar mensaje (admin)"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    queryset = Message.objects.all()
    lookup_field = 'id'







# client/views.py - Agregar vistas de reportes

from .models import Report
from .serializers import ReportSerializer, ReportCreateSerializer


class ReportCreateView(generics.CreateAPIView):
    """Crear un nuevo reporte"""
    serializer_class = ReportCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)


class AdminReportListView(generics.ListAPIView):
    """Listar reportes pendientes (solo admin)"""
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        return Report.objects.filter(resolved=False).order_by('-created_at')


class AdminReportDismissView(APIView):
    """Ignorar un reporte (admin)"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def post(self, request, report_id):
        try:
            report = Report.objects.get(id=report_id, resolved=False)
            report.resolved = True
            report.save()
            return Response({'status': 'dismissed', 'message': 'Reporte ignorado'})
        except Report.DoesNotExist:
            return Response(
                {'error': 'Reporte no encontrado o ya resuelto'},
                status=status.HTTP_404_NOT_FOUND
            )


class AdminReportResolveView(APIView):
    """Resolver reporte eliminando contenido (admin)"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def delete(self, request, report_id):
        try:
            report = Report.objects.get(id=report_id, resolved=False)
            
            # Eliminar el contenido según el tipo
            if report.content_type == Report.ContentType.POST:
                post = Post.objects.filter(id=report.content_id).first()
                if post:
                    post.delete()
            elif report.content_type == Report.ContentType.MESSAGE:
                message = Message.objects.filter(id=report.content_id).first()
                if message:
                    message.delete()
            elif report.content_type == Report.ContentType.USER:
                user = User.objects.filter(id=report.content_id).first()
                if user:
                    user.is_active = False
                    user.save()
            
            # Marcar reporte como resuelto
            report.resolved = True
            report.save()
            
            return Response({
                'status': 'resolved',
                'message': f'{report.get_content_type_display()} eliminado y reporte resuelto'
            })
        except Report.DoesNotExist:
            return Response(
                {'error': 'Reporte no encontrado o ya resuelto'},
                status=status.HTTP_404_NOT_FOUND
            )



class AdminUserActivityView(APIView):
    """Ver actividad reciente del usuario (admin)"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request, user_id):
        user = User.objects.get(id=user_id)
        activity = []
        
        # Productos recientes
        recent_posts = Post.objects.filter(seller=user).order_by('-created_at')[:10]
        for post in recent_posts:
            activity.append({
                'id': f"post_{post.id}",
                'icon': 'inventory',
                'color': 'primary',
                'description': f'Publicó el producto: "{post.description[:50]}"',
                'created_at': post.created_at,
                'link': f'/post/{post.id}'
            })
        
        # Mensajes recientes
        recent_messages = Message.objects.filter(seller=user).order_by('-created_at')[:10]
        for msg in recent_messages:
            activity.append({
                'id': f"msg_{msg.id}",
                'icon': 'chat',
                'color': 'info',
                'description': f'Publicó un mensaje: "{msg.content[:50]}"',
                'created_at': msg.created_at,
                'link': f'/message/{msg.id}'
            })
        
        # Seguidores recientes (nuevos follows)
        recent_followers = Follow.objects.filter(following=user).order_by('-created_at')[:10]
        for follow in recent_followers:
            activity.append({
                'id': f"follow_{follow.id}",
                'icon': 'person_add',
                'color': 'positive',
                'description': f'Nuevo seguidor: {follow.follower.store_name or follow.follower.username}',
                'created_at': follow.created_at,
                'link': f'/profile/{follow.follower.id}'
            })
        
        # Ordenar por fecha
        activity.sort(key=lambda x: x['created_at'], reverse=True)
        
        return Response(activity[:30])


class AdminUserDeleteView(generics.DestroyAPIView):
    """Eliminar usuario permanentemente (admin)"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    queryset = User.objects.all()
    lookup_field = 'id'
    
    def perform_destroy(self, instance):
        # Eliminar todos los contenidos asociados
        instance.posts.all().delete()
        instance.messages.all().delete()
        instance.delete()

class AdminUserToggleStoreView(APIView):
    """Activar/desactivar tienda de un usuario (admin)"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def post(self, request, user_id):
        user = User.objects.get(id=user_id)
        user.is_store_active = not user.is_store_active
        user.save()
        return Response({
            'status': 'toggled',
            'is_store_active': user.is_store_active,
            'message': f'Tienda {"activada" if user.is_store_active else "desactivada"}'
        })


class AdminUserResendVerificationView(APIView):
    """Reenviar email de verificación (admin)"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def post(self, request, user_id):
        user = User.objects.get(id=user_id)
        from .utils import send_verification_email
        
        success = send_verification_email(user, request)
        
        if success:
            return Response({
                'success': True,
                'message': f'Email de verificación enviado a {user.email}'
            })
        else:
            return Response({
                'success': False,
                'message': 'Error al enviar el email de verificación'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class AdminUserVerifyEmailView(APIView):
    """Verificar email de un usuario directamente (admin)"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            
            if user.email_verified:
                return Response({
                    'success': False,
                    'message': 'El email ya está verificado',
                    'email_verified': True
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Marcar email como verificado
            user.email_verified = True
            user.email_verification_token = None
            user.save()
            
            return Response({
                'success': True,
                'message': f'Email de {user.email} verificado correctamente',
                'email_verified': True,
                'user': UserSerializer(user, context={'request': request}).data
            })
            
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Usuario no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)


class AdminUserResendVerificationView(APIView):
    """Reenviar email de verificación (admin)"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            
            if user.email_verified:
                return Response({
                    'success': False,
                    'message': 'El email ya está verificado. No es necesario reenviar.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from .utils import send_verification_email
            
            success = send_verification_email(user, request)
            
            if success:
                return Response({
                    'success': True,
                    'message': f'Email de verificación enviado a {user.email}'
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Error al enviar el email de verificación'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Usuario no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)



from .serializers import SupportMessage, SupportMessageSerializer, SupportTicket, SupportTicketCreateSerializer, SupportTicketSerializer, FAQSerializer, FAQ


class UserTicketListView(generics.ListAPIView):
    """Listar tickets del usuario autenticado"""
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user).order_by('-created_at')


class UserTicketCreateView(generics.CreateAPIView):
    """Crear nuevo ticket de soporte"""
    serializer_class = SupportTicketCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserTicketDetailView(generics.RetrieveAPIView):
    """Ver detalle de un ticket"""
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)


class UserTicketMessageCreateView(generics.CreateAPIView):
    """Agregar mensaje a un ticket (usuarios)"""
    serializer_class = SupportMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        ticket = SupportTicket.objects.get(id=self.kwargs['ticket_id'])
        # Verificar que el ticket pertenece al usuario
        if ticket.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permiso para responder a este ticket")
        serializer.save(ticket=ticket, user=self.request.user, is_staff_reply=False)


# ==================== SOPORTE PARA ADMIN ====================
class AdminTicketListView(generics.ListAPIView):
    """Listar todos los tickets (admin)"""
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        queryset = SupportTicket.objects.all()
        status = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')
        if status:
            queryset = queryset.filter(status=status)
        if priority:
            queryset = queryset.filter(priority=priority)
        return queryset.order_by('-created_at')


class AdminTicketDetailView(generics.RetrieveUpdateAPIView):
    """Ver y actualizar ticket (admin)"""
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    queryset = SupportTicket.objects.all()
    lookup_field = 'id'


class AdminTicketAssignView(APIView):
    """Asignar ticket a un administrador"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def post(self, request, ticket_id):
        ticket = SupportTicket.objects.get(id=ticket_id)
        ticket.assigned_to = request.user
        ticket.status = SupportTicket.Status.IN_PROGRESS
        ticket.save()
        return Response({'status': 'assigned'})


class AdminTicketStatusView(APIView):
    """Cambiar estado de un ticket"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def post(self, request, ticket_id):
        ticket = SupportTicket.objects.get(id=ticket_id)
        status = request.data.get('status')
        if status in dict(SupportTicket.Status.choices):
            ticket.status = status
            if status == SupportTicket.Status.RESOLVED:
                from django.utils import timezone
                ticket.resolved_at = timezone.now()
            ticket.save()
            return Response({'status': 'updated'})
        return Response({'error': 'Estado inválido'}, status=status.HTTP_400_BAD_REQUEST)


class AdminTicketDeleteView(generics.DestroyAPIView):
    """Eliminar ticket (admin) - Solo para contenido problemático"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    queryset = SupportTicket.objects.all()
    lookup_field = 'id'


class AdminTicketReplyView(APIView):
    """Responder a un ticket (admin)"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def post(self, request, ticket_id):
        ticket = SupportTicket.objects.get(id=ticket_id)
        message = request.data.get('message')
        if not message:
            return Response({'error': 'El mensaje es requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear el mensaje como respuesta de staff
        support_message = SupportMessage.objects.create(
            ticket=ticket,
            user=request.user,
            message=message,
            is_staff_reply=True
        )
        
        # Cambiar estado a "esperando respuesta" si estaba en proceso
        if ticket.status == SupportTicket.Status.IN_PROGRESS:
            ticket.status = SupportTicket.Status.WAITING
            ticket.save()
        
        # Crear notificación para el usuario
        Notification.objects.create(
            user=ticket.user,
            type=Notification.Type.TICKET_REPLY,
            actor=request.user,
            ticket=ticket
        )
        
        serializer = SupportMessageSerializer(support_message, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)



# ==================== FAQ (Públicas + Admin) ====================
class FAQListView(generics.ListAPIView):
    """Listar preguntas frecuentes (público)"""
    serializer_class = FAQSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = FAQ.objects.filter(is_active=True)
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        return queryset.order_by('order', 'created_at')


class AdminFAQListView(generics.ListAPIView):
    """Listar todas las FAQs (admin)"""
    serializer_class = FAQSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        return FAQ.objects.all().order_by('order', 'created_at')


class AdminFAQCreateView(generics.CreateAPIView):
    """Crear FAQ (admin)"""
    serializer_class = FAQSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]


class AdminFAQUpdateView(generics.RetrieveUpdateDestroyAPIView):
    """Actualizar o eliminar FAQ (admin)"""
    serializer_class = FAQSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    queryset = FAQ.objects.all()
    lookup_field = 'id'









