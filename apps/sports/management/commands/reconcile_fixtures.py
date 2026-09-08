import time
import requests
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from sports.models import Fixture
from sports.tasks import get_headers, BASE_URL, save_fixture_from_api


class Command(BaseCommand):
    help = "Reconciles displaced/rescheduled fixtures against API-Football provider schedule."

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Specific date to reconcile in YYYY-MM-DD format (e.g. 2026-09-08)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=3,
            help='Number of days to check starting from today if --date is not provided (default: 3)',
        )

    def handle(self, *args, **options):
        date_arg = options.get('date')
        if date_arg:
            dates = [date_arg.strip()]
        else:
            days = options.get('days', 3)
            today = timezone.now().date()
            dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]

        self.stdout.write(self.style.SUCCESS(f"🚀 Starting fixture reconciliation for {len(dates)} dates: {', '.join(dates)}"))

        for date_str in dates:
            self.stdout.write(f"\n📅 Reconciling date: {date_str}...")
            url = f"{BASE_URL}/fixtures"
            params = {'date': date_str}

            try:
                response = requests.get(url, headers=get_headers(), params=params, timeout=20)
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"❌ API Error for {date_str}: HTTP {response.status_code}"))
                    continue

                api_data = response.json().get('response', [])
                api_ids = {item['fixture']['id'] for item in api_data}
                self.stdout.write(f"   Provider returned {len(api_data)} official fixtures for {date_str}.")

                # 1. Update/Save the official fixtures for this date
                with transaction.atomic():
                    for item in api_data:
                        save_fixture_from_api(item)

                # 2. Find displaced fixtures (in DB on this date, but not in provider response)
                db_ids = set(Fixture.objects.filter(date__date=date_str).values_list('id', flat=True))
                displaced_ids = list(db_ids - api_ids)

                if not displaced_ids:
                    self.stdout.write(self.style.SUCCESS(f"   ✅ All {len(db_ids)} fixtures on {date_str} are 100% verified."))
                    continue

                self.stdout.write(self.style.WARNING(f"   ⚠️ Found {len(displaced_ids)} displaced fixtures on {date_str}. Re-syncing real dates..."))

                chunk_size = 20
                reconciled_count = 0
                deleted_count = 0

                for i in range(0, len(displaced_ids), chunk_size):
                    if i > 0:
                        time.sleep(0.3)
                    chunk = displaced_ids[i:i + chunk_size]
                    ids_str = '-'.join(map(str, chunk))

                    try:
                        c_res = requests.get(url, headers=get_headers(), params={'ids': ids_str}, timeout=15)
                        c_data = c_res.json().get('response', [])
                        returned_ids = set()

                        with transaction.atomic():
                            for item in c_data:
                                save_fixture_from_api(item)
                                returned_ids.add(item['fixture']['id'])
                                reconciled_count += 1

                        # Fixtures no longer recognized by the provider
                        missing_in_api = set(chunk) - returned_ids
                        if missing_in_api:
                            deleted_num, _ = Fixture.objects.filter(id__in=missing_in_api).delete()
                            deleted_count += deleted_num

                    except Exception as err:
                        self.stdout.write(self.style.ERROR(f"   ❌ Error re-syncing chunk {chunk}: {err}"))

                final_count = Fixture.objects.filter(date__date=date_str).count()
                self.stdout.write(self.style.SUCCESS(
                    f"   ✅ Done! Reconciled {reconciled_count} fixtures to their new dates, deleted {deleted_count} stale. "
                    f"Final DB count for {date_str}: {final_count} (Matches provider exactly: {final_count == len(api_ids)})."
                ))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error reconciling {date_str}: {e}"))

        self.stdout.write(self.style.SUCCESS("\n🎉 Reconciliation completed successfully!"))
