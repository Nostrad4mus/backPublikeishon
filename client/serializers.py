# client/serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Follow, Post, Message, PostLike, MessageLike, Notification
from django.conf import settings


# ==================== USER SERIALIZERS ====================
class UserSerializer(serializers.ModelSerializer):
    rank_display = serializers.CharField(source='get_rank_display', read_only=True)
    remaining_products = serializers.IntegerField(read_only=True)
    remaining_messages = serializers.IntegerField(source='remaining_messages_this_month', read_only=True)
    has_store = serializers.BooleanField(read_only=True)
    can_create_product = serializers.BooleanField(read_only=True)
    can_create_message = serializers.BooleanField(read_only=True)
    avatar = serializers.SerializerMethodField()
    banner = serializers.SerializerMethodField()
    
    # Asegurar que estos campos se devuelven correctamente
    is_active = serializers.BooleanField(read_only=True)
    is_store_active = serializers.BooleanField(read_only=True)
    email_verified = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'website',
                  'bio', 'avatar', 'banner', 'store_name', 'store_description',
                  'is_store_active', 'is_active', 'is_staff', 'email_verified',
                  'rank', 'rank_display', 'max_products', 'max_messages',
                  'products_used', 'messages_used_this_month', 'remaining_products', 'remaining_messages',
                  'can_create_product', 'can_create_message', 'is_verified', 
                  'followers_count', 'following_count', 'has_store', 'created_at',
                  'notifications_email', 'notifications_orders', 'notifications_marketing']
        read_only_fields = ['id', 'rank', 'max_products', 'max_messages', 'products_used', 
                           'messages_used_this_month', 'followers_count', 'following_count', 
                           'created_at', 'remaining_products', 'remaining_messages', 'has_store',
                           'can_create_product', 'can_create_message', 'is_active', 
                           'is_store_active', 'email_verified']
    
    def get_avatar(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None
    
    def get_banner(self, obj):
        if obj.banner:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.banner.url)
            return obj.banner.url
        return None



class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 'last_name']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        user.rank = User.Rank.BASIC
        user.max_products = 1
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar usuario (admin puede modificar estados)"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'bio', 'avatar', 'banner',
            'store_name', 'store_description', 'is_store_active', 'is_active',
            'notifications_email', 'notifications_orders', 'notifications_marketing',
            'phone', 'website', 'rank', 'max_products', 'max_messages'
        ]
    
    def update(self, instance, validated_data):
        # Actualizar campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance



# ==================== POST SERIALIZERS (PRODUCTOS) ====================
class PostSerializer(serializers.ModelSerializer):
    seller = UserSerializer(read_only=True)
    is_liked_by_user = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = ['id', 'seller', 'images', 'description', 'price', 'stock', 
                  'category', 'likes_count', 'is_active', 'is_sold', 
                  'is_liked_by_user', 'created_at', 'updated_at']
        read_only_fields = ['likes_count', 'created_at', 'updated_at']
    
    def get_images(self, obj):
        request = self.context.get('request')
        if not obj.images:
            return []
        image_urls = []
        for img_path in obj.images:
            if img_path:
                if img_path.startswith('http'):
                    image_urls.append(img_path)
                else:
                    if request:
                        image_urls.append(request.build_absolute_uri(img_path))
                    else:
                        image_urls.append(f"{settings.MEDIA_URL}{img_path.lstrip('/media/')}")
        return image_urls
    
    def get_is_liked_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return PostLike.objects.filter(user=request.user, post=obj).exists()
        return False


class PostCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Post
        fields = ['description', 'price', 'stock', 'category', 'images']
    
    def validate(self, data):
        user = self.context['request'].user
        if not user.can_create_product():
            raise serializers.ValidationError({
                'error': f'Has alcanzado el límite de {user.max_products} productos. Actualiza tu plan para publicar más.'
            })
        return data
    
    def create(self, validated_data):
        images = validated_data.pop('images', [])
        seller = self.context['request'].user
        
        post = Post.objects.create(seller=seller, **validated_data)
        
        if images:
            image_urls = []
            for idx, img in enumerate(images):
                import os
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile
                
                ext = os.path.splitext(img.name)[1]
                filename = f"posts/{seller.id}_{post.id}_{idx}{ext}"
                path = default_storage.save(filename, ContentFile(img.read()))
                image_urls.append(default_storage.url(path))
            
            post.images = image_urls
            post.save()
        
        return post


class PostUpdateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    existing_images = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True
    )
    removed_images = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = Post
        fields = ['description', 'price', 'stock', 'category', 'images', 'existing_images', 'removed_images']
    
    def update(self, instance, validated_data):
        instance.description = validated_data.get('description', instance.description)
        instance.price = validated_data.get('price', instance.price)
        instance.stock = validated_data.get('stock', instance.stock)
        instance.category = validated_data.get('category', instance.category)
        
        existing_images = validated_data.get('existing_images', [])
        removed_images = validated_data.get('removed_images', [])
        new_images = validated_data.get('images', [])
        
        current_images = instance.images or []
        final_images = []
        
        for img in current_images:
            if img not in removed_images:
                final_images.append(img)
        
        for idx, img in enumerate(new_images):
            import os
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            
            ext = os.path.splitext(img.name)[1]
            filename = f"posts/{instance.seller.id}_{instance.id}_{len(final_images)}{ext}"
            path = default_storage.save(filename, ContentFile(img.read()))
            final_images.append(default_storage.url(path))
        
        instance.images = final_images
        instance.save()
        
        return instance


# ==================== MESSAGE SERIALIZERS ====================
class MessageSerializer(serializers.ModelSerializer):
    seller = UserSerializer(read_only=True)
    is_liked_by_user = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['id', 'seller', 'content', 'image', 'image_url', 'link', 
                  'likes_count', 'is_active', 'is_liked_by_user', 'created_at', 'updated_at']
        read_only_fields = ['likes_count', 'created_at', 'updated_at']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_is_liked_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return MessageLike.objects.filter(user=request.user, message=obj).exists()
        return False


class MessageCreateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = Message
        fields = ['content', 'image', 'link']
    
    def validate(self, data):
        user = self.context['request'].user
        if not user.can_create_message():
            raise serializers.ValidationError({
                'error': f'Has alcanzado el límite de {user.max_messages} mensajes este mes. Los mensajes se renuevan mensualmente.'
            })
        return data
    
    def create(self, validated_data):
        seller = self.context['request'].user
        return Message.objects.create(seller=seller, **validated_data)


class MessageUpdateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)
    remove_image = serializers.BooleanField(required=False, write_only=True)
    
    class Meta:
        model = Message
        fields = ['content', 'image', 'link', 'remove_image']
    
    def update(self, instance, validated_data):
        instance.content = validated_data.get('content', instance.content)
        instance.link = validated_data.get('link', instance.link)
        
        if validated_data.get('remove_image', False):
            instance.image = None
        elif 'image' in validated_data:
            instance.image = validated_data['image']
        
        instance.save()
        return instance


# ==================== FOLLOW SERIALIZER ====================
class FollowSerializer(serializers.ModelSerializer):
    follower = UserSerializer(read_only=True)
    following = UserSerializer(read_only=True)
    
    class Meta:
        model = Follow
        fields = ['id', 'follower', 'following', 'created_at']


# ==================== NOTIFICATION SERIALIZER ====================
class NotificationSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'user', 'type', 'type_display', 'actor', 'post', 'message', 'is_read', 'created_at']
        read_only_fields = ['id', 'user', 'type', 'actor', 'post', 'message', 'created_at']



from .models import Report

# Sección de Admin
class ReportSerializer(serializers.ModelSerializer):
    reported_by = UserSerializer(read_only=True)
    content = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    content_type_display = serializers.CharField(source='get_content_type_display', read_only=True)
    
    class Meta:
        model = Report
        fields = ['id', 'content_type', 'content_type_display', 'content_id', 'reported_by', 
                'type', 'type_display', 'reason', 'content', 'resolved', 'created_at']
        read_only_fields = ['id', 'created_at', 'resolved']
    
    def get_content(self, obj):
        request = self.context.get('request')
        if obj.content_type == Report.ContentType.POST:
            post = Post.objects.filter(id=obj.content_id).first()
            if post:
                return PostSerializer(post, context={'request': request}).data
        elif obj.content_type == Report.ContentType.MESSAGE:
            message = Message.objects.filter(id=obj.content_id).first()
            if message:
                return MessageSerializer(message, context={'request': request}).data
        elif obj.content_type == Report.ContentType.USER:
            user = User.objects.filter(id=obj.content_id).first()
            if user:
                return UserSerializer(user, context={'request': request}).data
        return None


class ReportCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear reportes"""
    
    class Meta:
        model = Report
        fields = ['content_type', 'content_id', 'type', 'reason']
    
    def validate(self, data):
        # Verificar que el contenido existe
        content_type = data['content_type']
        content_id = data['content_id']
        
        if content_type == Report.ContentType.POST:
            if not Post.objects.filter(id=content_id).exists():
                raise serializers.ValidationError('El producto no existe')
        elif content_type == Report.ContentType.MESSAGE:
            if not Message.objects.filter(id=content_id).exists():
                raise serializers.ValidationError('El mensaje no existe')
        elif content_type == Report.ContentType.USER:
            if not User.objects.filter(id=content_id).exists():
                raise serializers.ValidationError('El usuario no existe')
        
        # Verificar que no se haya reportado ya este contenido por el mismo usuario
        if Report.objects.filter(
            content_type=content_type,
            content_id=content_id,
            reported_by=self.context['request'].user,
            resolved=False
        ).exists():
            raise serializers.ValidationError('Ya has reportado este contenido')
        
        return data
    
    def create(self, validated_data):
        validated_data['reported_by'] = self.context['request'].user
        return Report.objects.create(**validated_data)



from .models import SupportTicket, SupportMessage, FAQ

class SupportMessageSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportMessage
        fields = ['id', 'user', 'user_name', 'user_avatar', 'message', 'is_staff_reply', 'attachment', 'created_at']
        read_only_fields = ['id', 'user', 'user_name', 'created_at']
    
    def get_user_avatar(self, obj):
        """Devolver URL completa del avatar del usuario"""
        if obj.user.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
            return obj.user.avatar.url
        return None



class SupportTicketSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    messages = SupportMessageSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    messages_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportTicket
        fields = ['id', 'user', 'user_name', 'user_email', 'user_avatar', 'title', 'description', 
                  'status', 'status_display', 'priority', 'priority_display', 
                  'category', 'attachment', 'assigned_to', 'messages', 'messages_count',
                  'created_at', 'updated_at', 'resolved_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'resolved_at']
    
    def get_user_avatar(self, obj):
        """Devolver URL completa del avatar del usuario"""
        if obj.user.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
            return obj.user.avatar.url
        return None
    
    def get_messages_count(self, obj):
        return obj.messages.count()



class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ['title', 'description', 'priority', 'category', 'attachment']


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ['id', 'question', 'answer', 'category', 'order', 'is_active']


