from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from licenses.models import UserRole

User = get_user_model()

class Command(BaseCommand):
    help = 'Crea un usuario con rol admin de licencias'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='superadmin', help='Nombre de usuario (default: superadmin)')
        parser.add_argument('--email', type=str, default='superadmin@example.com', help='Email del usuario (default: superadmin@example.com)')
        parser.add_argument('--password', type=str, default='admin123', help='Contraseña del usuario (default: admin123)')
        parser.add_argument('--first-name', type=str, default='Joe', help='Nombre (default: Joe)')
        parser.add_argument('--last-name', type=str, default='Doe', help='Apellido (default: Doe)')
        parser.add_argument('--rol', type=int, default=UserRole.ROLE_ADMIN, help='Rol del usuario: 1=superadmin, 2=admin, 3=user (default: 2)')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']
        rol = options['rol']
        
        # Validar que el rol sea válido
        valid_roles = [UserRole.ROLE_SUPERADMIN, UserRole.ROLE_ADMIN, UserRole.ROLE_USER]
        if rol not in valid_roles:
            self.stdout.write(
                self.style.ERROR(f'Rol inválido. Debe ser: 1=superadmin, 2=admin, 3=user')
            )
            return
        
        # Verificar si el usuario ya existe
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'El usuario {username} ya existe. Actualizando...')
            )
            user = User.objects.get(username=username)
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.set_password(password)
            user.is_staff = True
            user.is_active = True
            user.save()
        else:
            # Crear usuario
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=True,
                is_active=True
            )
            self.stdout.write(
                self.style.SUCCESS(f'Usuario creado exitosamente: {username}')
            )
        
        # Asignar o actualizar rol
        user_role, created = UserRole.objects.get_or_create(
            user=user,
            defaults={'rol': rol}
        )
        
        if not created:
            user_role.rol = rol
            user_role.save()
            self.stdout.write(
                self.style.SUCCESS(f'Rol {user_role.get_rol_display()} asignado al usuario: {username}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Rol {user_role.get_rol_display()} creado y asignado al usuario: {username}')
            )
        
        rol_display = dict(UserRole.ROLE_CHOICES).get(rol, 'Unknown')
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Usuario creado/actualizado exitosamente:\n'
                f'  Username: {username}\n'
                f'  Email: {email}\n'
                f'  Password: {password}\n'
                f'  First Name: {first_name}\n'
                f'  Last Name: {last_name}\n'
                f'  Rol: {rol} ({rol_display})'
            )
        )