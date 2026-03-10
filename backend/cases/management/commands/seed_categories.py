from django.core.management.base import BaseCommand

from cases.models import CaseCategory


CATEGORIES = [
    ('Enforced disappearance', 'Person taken by state actors, whereabouts unknown'),
    ('Arbitrary detention', 'Detained without due process or legal basis'),
    ('Restricted movement', 'House arrest, travel ban, or movement restrictions'),
    ('Stateless', 'Denied citizenship or identity documents'),
    ('Rights restricted', 'Denied education, employment, religious freedom, or other basic rights'),
    ('Refugee / needs relocation', 'Needs help leaving country or resettlement'),
    ('Extrajudicial violence', 'Physical harm by state or state-affiliated actors outside legal process'),
    ('Other', 'Other forms of oppression or need for assistance'),
]


class Command(BaseCommand):
    help = 'Seed default case categories'

    def handle(self, *args, **options):
        for name, desc in CATEGORIES:
            obj, created = CaseCategory.objects.get_or_create(
                name=name, defaults={'description': desc}
            )
            status = 'created' if created else 'exists'
            self.stdout.write(f'  {status}: {name}')
        self.stdout.write(self.style.SUCCESS('Done.'))
