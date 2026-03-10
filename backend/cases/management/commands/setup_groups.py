from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


GROUPS = {
    'Volunteer': [
        'cases.add_report', 'cases.change_report', 'cases.view_report',
        'cases.add_media', 'cases.change_media', 'cases.view_media',
        'cases.view_person', 'cases.add_person', 'cases.change_person',
        'cases.view_casecategory',
        'cases.view_familyrelationship',
    ],
    'Advocate': [
        # All volunteer permissions plus:
        'cases.add_report', 'cases.change_report', 'cases.view_report',
        'cases.add_media', 'cases.change_media', 'cases.view_media', 'cases.delete_media',
        'cases.view_person', 'cases.add_person', 'cases.change_person',
        'cases.view_casecategory',
        'cases.view_familyrelationship', 'cases.add_familyrelationship',
        'cases.change_familyrelationship', 'cases.delete_familyrelationship',
        # Casework
        'casework.add_caseworkrecord', 'casework.change_caseworkrecord',
        'casework.view_caseworkrecord', 'casework.delete_caseworkrecord',
        # Contacts
        'contacts.add_contact', 'contacts.change_contact',
        'contacts.view_contact', 'contacts.delete_contact',
    ],
}


class Command(BaseCommand):
    help = 'Create permission groups: Volunteer, Advocate'

    def handle(self, *args, **options):
        for group_name, perm_codenames in GROUPS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            status = 'created' if created else 'exists'
            self.stdout.write(f'  {status}: {group_name}')

            group.permissions.clear()
            for codename in set(perm_codenames):
                app_label, code = codename.split('.')
                try:
                    perm = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=code,
                    )
                    group.permissions.add(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'    skip: {codename} not found'))

            self.stdout.write(f'    {group.permissions.count()} permissions assigned')

        self.stdout.write(self.style.SUCCESS('Done.'))
