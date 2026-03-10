"""
Import legacy data from the old Raise the Voices 'testimony' database
into the new testimonies_world schema.

Usage:
    python manage.py import_legacy [--dry-run]

Connects read-only to the 'testimony' database on VM 100 and imports:
- victims → Person
- victim_translations (English) → Person fields (summary, medical, etc.)
- incidents + incident_translations → Report
- reports (old 1:1 reporter metadata) → merged into Report
- victim_media + incident_media → Media

Does NOT import: old users, soft-deleted records, non-English translations.
"""

import psycopg2
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from cases.models import CaseCategory, Media, Person, Report

User = get_user_model()

# Old status values → new status choices
STATUS_MAP = {
    'All': 'unknown',
    'abused': 'rights_restricted',
    'injured': 'detained',
}

# Old health_status → new medical_status
MEDICAL_MAP = {
    'All': 'unknown',
    'current': 'healthy',
    'health': 'health_concerns',
}

# Media tag → (media_type, visibility)
MEDIA_TAG_MAP = {
    'documents': ('document', 'restricted'),
    'victim_external': ('link', 'public'),
    'incidents': ('photo', 'public'),
    'incidents_external': ('link', 'public'),
}


class Command(BaseCommand):
    help = 'Import legacy data from the old testimony database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without writing to the database',
        )
        parser.add_argument(
            '--legacy-user', default='cobox',
            help='Legacy database user (default: cobox)',
        )
        parser.add_argument(
            '--legacy-password', default='',
            help='Legacy database password (reads from pgpass if empty)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Get or create admin user for created_by
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stderr.write('No superuser found. Create one first.')
            return

        # Ensure categories exist
        disappearance_cat, _ = CaseCategory.objects.get_or_create(
            name='Enforced disappearance',
            defaults={'description': 'Enforced disappearance by state or non-state actors'},
        )
        detention_cat, _ = CaseCategory.objects.get_or_create(
            name='Arbitrary detention',
            defaults={'description': 'Detention without due process'},
        )
        rights_cat, _ = CaseCategory.objects.get_or_create(
            name='Rights restricted',
            defaults={'description': 'Fundamental rights restricted by state action'},
        )

        # Connect to legacy database (read-only) using cobox admin credentials
        connect_kwargs = {
            'host': settings.DATABASES['default']['HOST'],
            'port': settings.DATABASES['default']['PORT'],
            'dbname': 'testimony',
            'user': options['legacy_user'],
        }
        if options['legacy_password']:
            connect_kwargs['password'] = options['legacy_password']
        else:
            # Use pgpass
            connect_kwargs['passfile'] = '/home/golda/.pgpass'

        legacy_conn = psycopg2.connect(**connect_kwargs)
        legacy_conn.set_session(readonly=True)
        cur = legacy_conn.cursor()

        # Track old_id → new Person for linking
        id_map = {}
        stats = {
            'persons': 0,
            'reports': 0,
            'media': 0,
            'skipped': 0,
        }

        # --- VICTIMS → PERSON ---
        cur.execute("""
            SELECT v.id, v.name, v.legal_name, v.aliases, v.country,
                   v.current_status, v.gender, v.place_of_birth,
                   v.date_of_birth, v.last_seen_date, v.last_seen_place,
                   v.profile_image_url, v.created_at,
                   vt.about_the_victim, vt.health_status, vt.health_issues,
                   vt.nationality, vt.profession, vt.additional_information,
                   vt.languages_spoken
            FROM victims v
            LEFT JOIN victim_translations vt
                ON vt.victim_id = v.id AND vt.language = 'en' AND vt.deleted_at IS NULL
            WHERE v.deleted_at IS NULL
            ORDER BY v.id
        """)
        victims = cur.fetchall()

        self.stdout.write(f'Found {len(victims)} active victims to import')

        for row in victims:
            (old_id, name, legal_name, aliases, country,
             current_status, gender, place_of_birth,
             date_of_birth, last_seen_date, last_seen_place,
             profile_image_url, created_at,
             about_the_victim, health_status, health_issues,
             nationality, profession, additional_info,
             languages_spoken) = row

            # Check if already imported (by name + country)
            if Person.objects.filter(name__iexact=name.strip(), country=country).exists():
                self.stdout.write(f'  SKIP (exists): {name} ({country})')
                stats['skipped'] += 1
                existing = Person.objects.filter(
                    name__iexact=name.strip(), country=country
                ).first()
                id_map[old_id] = existing
                continue

            # Build summary narrative from translations
            parts = []
            if about_the_victim:
                parts.append(about_the_victim.strip())
            if profession:
                parts.append(f'Profession: {profession.strip()}')
            if languages_spoken:
                parts.append(f'Languages spoken: {languages_spoken.strip()}')
            if additional_info:
                parts.append(additional_info.strip())
            if place_of_birth:
                parts.append(f'Place of birth: {place_of_birth.strip()}')

            mapped_status = STATUS_MAP.get(current_status, 'unknown')
            mapped_medical = MEDICAL_MAP.get(health_status, 'unknown') if health_status else 'unknown'
            mapped_gender = gender if gender in ('M', 'F') else None

            dob = date_of_birth.date() if date_of_birth else None
            last_known = last_seen_date.date() if last_seen_date else None

            # Truncate long CharFields, move overflow to summary
            rough_loc = (last_seen_place or '').strip()
            if len(rough_loc) > 255:
                parts.append(f'Last seen location detail: {rough_loc}')
                rough_loc = rough_loc[:252] + '...'
            legal = (legal_name or '')[:255]
            alias = (aliases or '')[:255]

            summary = '\n\n'.join(parts)

            if dry_run:
                self.stdout.write(
                    f'  [DRY RUN] Would create Person: {name} ({country}) '
                    f'status={mapped_status} medical={mapped_medical}'
                )
                stats['persons'] += 1
                continue

            person = Person.objects.create(
                name=name.strip().title(),
                legal_name=legal,
                aliases=alias,
                country=country,
                current_status=mapped_status,
                medical_status=mapped_medical,
                medical_notes=health_issues or '',
                gender=mapped_gender or '',
                date_of_birth=dob,
                last_known_date=last_known,
                rough_location=rough_loc,
                summary_narrative=summary,
                ethnicity=nationality or '',
                is_published=True,
                created_by=admin_user,
            )

            if mapped_status == 'detained':
                person.categories.add(detention_cat)
            if mapped_status == 'rights_restricted':
                person.categories.add(rights_cat)

            if profile_image_url:
                Media.objects.create(
                    person=person,
                    url=profile_image_url,
                    media_type='photo',
                    visibility='public',
                    description='Profile image (imported)',
                    uploaded_by=admin_user,
                )
                stats['media'] += 1

            id_map[old_id] = person
            stats['persons'] += 1
            self.stdout.write(f'  Created Person #{person.id}: {person.name} ({country})')

        # --- INCIDENTS + INCIDENT_TRANSLATIONS → REPORT ---
        cur.execute("""
            SELECT i.id, i.victim_id, i.date_of_incident, i.location,
                   i.is_disappearance, i.created_at,
                   it.narrative_of_incident, it.current_status_summary
            FROM incidents i
            LEFT JOIN incident_translations it
                ON it.incident_id = i.id AND it.language = 'en' AND it.deleted_at IS NULL
            WHERE i.deleted_at IS NULL
            ORDER BY i.victim_id, i.id
        """)
        incidents = cur.fetchall()

        # Get old reports table for reporter metadata (1:1 with victim)
        cur.execute("""
            SELECT victim_id, name_of_reporter, email_of_reporter,
                   discovery, is_direct_testimony, state
            FROM reports
            WHERE deleted_at IS NULL
        """)
        reporter_meta = {}
        for rrow in cur.fetchall():
            reporter_meta[rrow[0]] = {
                'reporter_name': rrow[1] or '',
                'reporter_contact': rrow[2] or '',
                'source_attribution': rrow[3] or '',
                'is_direct': rrow[4],
                'state': rrow[5],
            }

        self.stdout.write(f'\nFound {len(incidents)} incidents to import as reports')

        for row in incidents:
            (inc_id, victim_id, date_of_incident, location,
             is_disappearance, inc_created_at,
             narrative, status_summary) = row

            person = id_map.get(victim_id)
            if not person:
                self.stdout.write(f'  SKIP incident {inc_id}: no person for victim_id={victim_id}')
                continue

            # Skip if report already exists for this person with same date
            if date_of_incident and Report.objects.filter(
                person=person, date_start=date_of_incident.date()
            ).exists():
                self.stdout.write(f'  SKIP report (exists): {person.name} {date_of_incident.date()}')
                continue

            narrative_text = narrative or ''
            if status_summary:
                narrative_text += f'\n\nCurrent status summary: {status_summary}'
            narrative_text = narrative_text.strip()

            if not narrative_text:
                narrative_text = '(No narrative provided in legacy data)'

            meta = reporter_meta.get(victim_id, {})
            source_type = 'firsthand' if meta.get('is_direct') else 'secondhand'
            is_private = meta.get('state') != 'published'

            # Truncate source_attribution (discovery), move overflow to narrative
            source_attr = (meta.get('source_attribution', '') or '').strip()
            if len(source_attr) > 500:
                narrative_text += f'\n\nSource discovery: {source_attr}'
                source_attr = source_attr[:497] + '...'

            # Truncate report location if needed
            report_loc = (location or '').strip()
            if len(report_loc) > 255:
                narrative_text += f'\n\nDetailed location: {report_loc}'
                report_loc = report_loc[:252] + '...'

            report_date = date_of_incident.date() if date_of_incident else None

            if dry_run:
                self.stdout.write(
                    f'  [DRY RUN] Would create Report for {person.name}: '
                    f'{narrative_text[:60]}...'
                )
                stats['reports'] += 1
                continue

            report = Report.objects.create(
                person=person,
                source_type=source_type,
                source_attribution=source_attr,
                reporter_name=(meta.get('reporter_name', '') or '')[:255],
                reporter_contact=(meta.get('reporter_contact', '') or '')[:500],
                date_start=report_date,
                rough_location=report_loc,
                narrative=narrative_text,
                is_private=is_private,
                created_by=admin_user,
            )

            if is_disappearance and not person.categories.filter(
                id=disappearance_cat.id
            ).exists():
                person.categories.add(disappearance_cat)

            stats['reports'] += 1
            self.stdout.write(f'  Created Report #{report.id} for {person.name}')

            # --- INCIDENT_MEDIA → MEDIA (linked to report) ---
            cur2 = legacy_conn.cursor()
            cur2.execute("""
                SELECT media_url, tag, date_of_media
                FROM incident_media
                WHERE incident_id = %s AND deleted_at IS NULL
            """, (inc_id,))
            for mrow in cur2.fetchall():
                media_url, tag, date_of_media = mrow
                mtype, vis = MEDIA_TAG_MAP.get(tag, ('link', 'public'))
                desc = 'Imported from legacy incident media'
                if date_of_media:
                    desc += f' ({date_of_media.date()})'

                Media.objects.create(
                    person=person,
                    report=report,
                    url=media_url,
                    media_type=mtype,
                    visibility=vis,
                    description=desc,
                    uploaded_by=admin_user,
                )
                stats['media'] += 1
            cur2.close()

        # --- VICTIM_MEDIA → MEDIA (linked to person only) ---
        cur.execute("""
            SELECT victim_id, media_url, tag, date_of_media
            FROM victim_media
            WHERE deleted_at IS NULL
            ORDER BY victim_id
        """)
        victim_media_rows = cur.fetchall()
        self.stdout.write(f'\nFound {len(victim_media_rows)} victim media to import')

        for mrow in victim_media_rows:
            victim_id, media_url, tag, date_of_media = mrow
            person = id_map.get(victim_id)
            if not person:
                continue

            if Media.objects.filter(person=person, url=media_url).exists():
                continue

            mtype, vis = MEDIA_TAG_MAP.get(tag, ('link', 'public'))
            desc = 'Imported from legacy victim media'
            if date_of_media:
                desc += f' ({date_of_media.date()})'

            if dry_run:
                self.stdout.write(f'  [DRY RUN] Would create Media: {media_url[:60]}')
                stats['media'] += 1
                continue

            Media.objects.create(
                person=person,
                url=media_url,
                media_type=mtype,
                visibility=vis,
                description=desc,
                uploaded_by=admin_user,
            )
            stats['media'] += 1

        cur.close()
        legacy_conn.close()

        # Summary
        self.stdout.write('\n' + '=' * 50)
        prefix = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(f'{prefix}Import complete:')
        self.stdout.write(f'  Persons created: {stats["persons"]}')
        self.stdout.write(f'  Persons skipped (already exist): {stats["skipped"]}')
        self.stdout.write(f'  Reports created: {stats["reports"]}')
        self.stdout.write(f'  Media created: {stats["media"]}')
