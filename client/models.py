# client/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# ==================== USER MODEL ====================
class User(AbstractUser):
    """Modelo de usuario unificado - todos pueden vender"""
    
    class Rank(models.TextChoices):
        BASIC = 'basic', 'Básico'
        PREMIUM = 'premium', 'Premium'
        VIP = 'vip', 'VIP'
    
    
    
    # Perfil público
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    banner = models.ImageField(upload_to='banners/', blank=True, null=True)
    
    # Datos de tienda
    store_name = models.CharField(max_length=100, blank=True, null=True)
    store_description = models.TextField(blank=True, null=True)
    is_store_active = models.BooleanField(default=False)
    
    # Contacto
    phone = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    # Preferencias
    notifications_email = models.BooleanField(default=True)
    notifications_orders = models.BooleanField(default=True)
    notifications_marketing = models.BooleanField(default=False)
    
    # Rangos y límites
    rank = models.CharField(max_length=10, choices=Rank.choices, default=Rank.BASIC)
    max_products = models.IntegerField(default=1)      # Límite de productos
    max_messages = models.IntegerField(default=50)      # Límite de mensajes por mes
    products_used = models.IntegerField(default=0)      # Productos actuales
    messages_used_this_month = models.IntegerField(default=0)  # Mensajes este mes
    
    is_verified = models.BooleanField(default=False)
    
    # Métricas
    followers_count = models.IntegerField(default=0)
    following_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    # Verificación de cuenta
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(blank=True, null=True)
    
    
    # Recuperación de contraseña
    password_reset_token = models.CharField(max_length=100, blank=True, null=True)
    password_reset_sent_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return self.username
    
    @property
    def has_store(self):
        return self.is_store_active and bool(self.store_name)
    
    @property
    def remaining_products(self):
        return max(0, self.max_products - self.products_used)
    
    @property
    def remaining_messages_this_month(self):
        return max(0, self.max_messages - self.messages_used_this_month)
    
    def can_create_product(self):
        """Verifica si puede crear un nuevo producto"""
        return self.is_store_active and self.remaining_products > 0
    
    def can_create_message(self):
        """Verifica si puede crear un nuevo mensaje"""
        return self.is_store_active and self.remaining_messages_this_month > 0
    
    def increment_products_used(self):
        """Incrementa el contador de productos usados"""
        self.products_used += 1
        self.save(update_fields=['products_used'])
    
    def decrement_products_used(self):
        """Decrementa el contador de productos usados"""
        self.products_used = max(0, self.products_used - 1)
        self.save(update_fields=['products_used'])
    
    def increment_messages_used(self):
        """Incrementa el contador de mensajes usados este mes"""
        self.messages_used_this_month += 1
        self.save(update_fields=['messages_used_this_month'])
    
    def decrement_messages_used(self):
        """Decrementa el contador de mensajes usados este mes"""
        self.messages_used_this_month = max(0, self.messages_used_this_month - 1)
        self.save(update_fields=['messages_used_this_month'])


# ==================== FOLLOW MODEL ====================
class Follow(models.Model):
    """Sistema de seguimiento"""
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['follower', 'following']
    
    def __str__(self):
        return f"{self.follower.username} sigue a {self.following.username}"


# ==================== POST MODEL (PRODUCTOS) ====================
class Post(models.Model):
    """Modelo de productos/publicaciones de venta"""
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    
    # Contenido
    images = models.JSONField(default=list)  # Lista de URLs de imágenes
    description = models.TextField(blank=True)
    
    # Datos de producto
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.IntegerField(default=1)
    category = models.CharField(max_length=100, blank=True)
    
    # Métricas
    likes_count = models.IntegerField(default=0)
    
    # Estado
    is_active = models.BooleanField(default=True)
    is_sold = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Producto by {self.seller.username} - {self.created_at.strftime('%Y-%m-%d')}"


# ==================== MESSAGE MODEL ====================
class Message(models.Model):
    """Modelo de mensajes/publicaciones de texto"""
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='messages')
    
    # Contenido
    content = models.TextField()
    image = models.ImageField(upload_to='messages/', blank=True, null=True)
    link = models.URLField(blank=True, null=True, max_length=500)
    
    # Métricas
    likes_count = models.IntegerField(default=0)
    
    # Estado
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Mensaje by {self.seller.username} - {self.created_at.strftime('%Y-%m-%d')}"


# ==================== LIKE MODELS ====================
class PostLike(models.Model):
    """Me gusta en productos"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'post']
    
    def __str__(self):
        return f"{self.user.username} like product {self.post.id}"


class MessageLike(models.Model):
    """Me gusta en mensajes"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'message']
    
    def __str__(self):
        return f"{self.user.username} like message {self.message.id}"


# ==================== NOTIFICATION MODEL ====================
class Notification(models.Model):
    class Type(models.TextChoices):
        FOLLOW = 'follow', 'Nuevo seguidor'
        LIKE_POST = 'like_post', 'Me gusta en producto'
        LIKE_MESSAGE = 'like_message', 'Me gusta en mensaje'
        NEW_POST = 'new_post', 'Nuevo producto'
        NEW_MESSAGE = 'new_message', 'Nuevo mensaje'
        TICKET_REPLY = 'ticket_reply', 'Respuesta en ticket de soporte'
        ORDER = 'order', 'Nuevo pedido'
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=Type.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications_actor')
    post = models.ForeignKey('Post', on_delete=models.CASCADE, null=True, blank=True)
    message = models.ForeignKey('Message', on_delete=models.CASCADE, null=True, blank=True)
    ticket = models.ForeignKey('SupportTicket', on_delete=models.CASCADE, null=True, blank=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.type} - {self.user.username}"



# ==================== SIGNALS ====================
@receiver(post_save, sender=Post)
def update_user_counts_on_post_create(sender, instance, created, **kwargs):
    """Actualiza contadores del usuario al crear un producto"""
    if created and instance.is_active:
        user = instance.seller
        user.increment_products_used()


@receiver(post_delete, sender=Post)
def update_user_counts_on_post_delete(sender, instance, **kwargs):
    """Actualiza contadores del usuario al eliminar un producto"""
    user = instance.seller
    user.decrement_products_used()


@receiver(post_save, sender=Message)
def update_user_counts_on_message_create(sender, instance, created, **kwargs):
    """Actualiza contadores del usuario al crear un mensaje"""
    if created and instance.is_active:
        user = instance.seller
        user.increment_messages_used()


@receiver(post_delete, sender=Message)
def update_user_counts_on_message_delete(sender, instance, **kwargs):
    """Actualiza contadores del usuario al eliminar un mensaje"""
    user = instance.seller
    user.decrement_messages_used()


class Report(models.Model):
    """Modelo para reportes de contenido inapropiado"""
    
    class ContentType(models.TextChoices):
        POST = 'post', 'Producto'
        MESSAGE = 'message', 'Mensaje'
        USER = 'user', 'Usuario'
    
    class Type(models.TextChoices):
        INAPPROPRIATE = 'inappropriate', 'Contenido inapropiado'
        SPAM = 'spam', 'Spam'
        FAKE = 'fake', 'Producto falso'
        OTHER = 'other', 'Otro'
    
    content_type = models.CharField(max_length=10, choices=ContentType.choices)
    content_id = models.IntegerField()
    reported_by = models.ForeignKey('User', on_delete=models.CASCADE, related_name='reports')
    type = models.CharField(max_length=20, choices=Type.choices)
    reason = models.TextField()
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Reporte de {self.reported_by.username} - {self.get_type_display()}"


# Soporte Técnico
class SupportTicket(models.Model):
    """Modelo de tickets de soporte"""
    
    class Status(models.TextChoices):
        OPEN = 'open', 'Abierto'
        IN_PROGRESS = 'in_progress', 'En proceso'
        WAITING = 'waiting', 'Esperando respuesta'
        RESOLVED = 'resolved', 'Resuelto'
        CLOSED = 'closed', 'Cerrado'
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Baja'
        MEDIUM = 'medium', 'Media'
        HIGH = 'high', 'Alta'
        URGENT = 'urgent', 'Urgente'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets')
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    category = models.CharField(max_length=50, blank=True, null=True)
    attachment = models.FileField(upload_to='support/', blank=True, null=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Ticket #{self.id} - {self.title}"


class SupportMessage(models.Model):
    """Mensajes dentro de un ticket"""
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_messages')
    message = models.TextField()
    is_staff_reply = models.BooleanField(default=False)
    attachment = models.FileField(upload_to='support/messages/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Mensaje en ticket #{self.ticket.id} - {self.user.username}"


class FAQ(models.Model):
    """Preguntas frecuentes"""
    question = models.CharField(max_length=300)
    answer = models.TextField()
    category = models.CharField(max_length=50, blank=True, null=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return self.question
