from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from licenses.models import UserLicense

# NUEVO: notificaciones
from notifications.signals import notify
from notifications.models import Notification
from django.utils.translation import gettext as _

def send_notification_email(license_obj, days_left):
    owner_email = getattr(license_obj.owner, 'email', None)
    if not owner_email:
        return
    subject = f'Tu licencia vence en {days_left} días'
    body = f'Hola, tu licencia del plan {license_obj.plan.plan_name} para la empresa {license_obj.company} vence el {license_obj.end_date}.'
    try:
        send_mail(subject, body, None, [owner_email], fail_silently=True)
    except Exception:
        pass

def send_inapp_notification(license_obj, days_left, today):
    owner = license_obj.owner
    if not owner:
        return

    # Evitar duplicados el mismo día para el mismo aviso
    verb = f'La licencia vence en {days_left} día(s)'
    if Notification.objects.filter(
        recipient=owner,
        verb=verb,
        timestamp__date=today
    ).exists():
        return

    # Mensajes multi-idioma en data (tu template usa data.verb_es si existe)
    data = {
        'verb_es': f'Tu licencia del plan {license_obj.plan.plan_name} para la empresa {license_obj.company} vence en {days_left} día(s). Fecha de vencimiento: {license_obj.end_date}.',
        'verb_fr': f'Votre licence du plan {license_obj.plan.plan_name} pour l’entreprise {license_obj.company} expire dans {days_left} jour(s). Expire le {license_obj.end_date}.',
        'verb_de': f'Ihre Lizenz für den Plan {license_obj.plan.plan_name} des Unternehmens {license_obj.company} läuft in {days_left} Tag(en) ab. Ablaufdatum: {license_obj.end_date}.',
        'verb_ar': f'ستنتهي صلاحية الترخيص للخطة {license_obj.plan.plan_name} لشركة {license_obj.company} خلال {days_left} يوم(أيام). تاريخ الانتهاء: {license_obj.end_date}.',
    }

    # actor = la empresa (texto), recipient = propietario
    try:
        notify.send(
            license_obj.company,            # actor
            recipient=owner,                # destinatario
            verb=verb,                      # fallback si no hay data.* en el template
            data=data
        )
    except Exception:
        pass

class Command(BaseCommand):
    help = 'Revisa licencias para expirar/recordatorios y desactiva expiradas'

    def handle(self, *args, **options):
        today = timezone.now().date()

        # Desactivar expiradas
        expired = UserLicense.objects.filter(is_active=True, end_date__lt=today).all()
        for lic in expired:
            lic.license_status = 'expired'
            lic.is_active = False
            lic.save(update_fields=['license_status', 'is_active'])
            self.stdout.write(self.style.WARNING(f'Licencia expirada desactivada: {lic.id}'))

            # Notificación de expiración (día 0)
            send_inapp_notification(lic, 0, today)

        # Recordatorios 30, 15, 7, 3, 1 días
        for days in (30, 15, 7, 3, 1):
            target = today + timedelta(days=days)
            to_notify = UserLicense.objects.filter(
                is_active=True,
                license_status='active',
                end_date=target
            )
            for lic in to_notify:
                send_notification_email(lic, days)     # email opcional
                send_inapp_notification(lic, days, today)  # notificación en campana
                # Si prefieres flags separados por hito, agrega más campos. Este es global.
                lic.renewal_reminder_sent = True
                lic.save(update_fields=['renewal_reminder_sent'])
                self.stdout.write(self.style.SUCCESS(f'Notificado {days} días antes: {lic.id}'))