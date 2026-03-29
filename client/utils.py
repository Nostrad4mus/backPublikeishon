# client/utils.py - Crear nuevo archivo
import secrets
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging
from .models import User
from django.utils import timezone

logger = logging.getLogger(__name__)

def generate_verification_token():
    """Genera un token único para verificación de email"""
    return secrets.token_urlsafe(32)


def send_verification_email(user, request):
    """Envía email de verificación al usuario"""
    try:
        # Generar token si no existe
        if not user.email_verification_token:
            user.email_verification_token = generate_verification_token()
            user.save()
        
        # Construir URL de verificación
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{user.email_verification_token}"
        
        # Contexto para el template
        context = {
            'user': user,
            'verification_url': verification_url,
            'site_name': 'SocialMarket',
            'support_email': settings.DEFAULT_FROM_EMAIL
        }
        
        # Renderizar plantilla HTML
        html_message = render_to_string('emails/verification_email.html', context)
        plain_message = strip_tags(html_message)
        
        # Enviar email
        send_mail(
            subject='Verifica tu cuenta en SocialMarket',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        user.email_verification_sent_at = timezone.now()
        user.save()
        
        logger.info(f"Email de verificación enviado a {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error al enviar email de verificación: {e}")
        return False


def resend_verification_email(user, request):
    """Reenviar email de verificación"""
    # Regenerar token
    user.email_verification_token = generate_verification_token()
    user.save()
    return send_verification_email(user, request)


def verify_email(token):
    """Verifica el email usando el token"""
    try:
        user = User.objects.get(email_verification_token=token)
        if not user.email_verified:
            user.email_verified = True
            user.email_verification_token = None
            user.save()
            return True, user
        return False, user
    except User.DoesNotExist:
        return False, None





# ==================== RECUPERACIÓN DE CONTRASEÑA ====================
def generate_password_reset_token():
    """Genera un token único para recuperación de contraseña"""
    return secrets.token_urlsafe(32)


def send_password_reset_email(email, request):
    """Envía email de recuperación de contraseña"""
    try:
        user = User.objects.get(email=email)
        
        # Generar token
        user.password_reset_token = generate_password_reset_token()
        user.password_reset_sent_at = timezone.now()
        user.save()
        
        # Construir URL de recuperación
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{user.password_reset_token}"
        
        # Contexto para el template
        context = {
            'user': user,
            'reset_url': reset_url,
            'site_name': 'SocialMarket',
            'support_email': settings.DEFAULT_FROM_EMAIL
        }
        
        # Renderizar plantilla HTML
        html_message = render_to_string('emails/password_reset_email.html', context)
        plain_message = strip_tags(html_message)
        
        # Enviar email
        send_mail(
            subject='Recupera tu contraseña en SocialMarket',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email de recuperación enviado a {user.email}")
        return True, None
        
    except User.DoesNotExist:
        logger.warning(f"Intento de recuperación para email no registrado: {email}")
        return False, 'El correo electrónico no está registrado en nuestra plataforma.'
    except Exception as e:
        logger.error(f"Error al enviar email de recuperación: {e}")
        return False, 'Error al enviar el email. Intenta nuevamente.'


def validate_password_reset_token(token):
    """Valida el token de recuperación de contraseña"""
    try:
        user = User.objects.get(password_reset_token=token)
        # Verificar que el token no tenga más de 24 horas
        if user.password_reset_sent_at:
            time_diff = timezone.now() - user.password_reset_sent_at
            if time_diff.total_seconds() > 86400:  # 24 horas
                return False, None, 'El enlace ha expirado. Solicita uno nuevo.'
        return True, user, None
    except User.DoesNotExist:
        return False, None, 'Token inválido o ya fue utilizado.'


def reset_password(token, new_password):
    """Restablece la contraseña usando el token"""
    valid, user, error = validate_password_reset_token(token)
    
    if not valid:
        return False, error
    
    # Establecer nueva contraseña
    user.set_password(new_password)
    user.password_reset_token = None
    user.password_reset_sent_at = None
    user.save()
    
    logger.info(f"Contraseña restablecida para usuario: {user.email}")
    return True, 'Contraseña actualizada exitosamente.'