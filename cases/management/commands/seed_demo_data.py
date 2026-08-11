"""
Management command: seed_demo_data

Creates demo fixtures:
  - 1 lawyer user  (demo_lawyer / demo12345)
  - 3 clients belonging to that lawyer
  - 5 case files across those clients (mixed statuses)
  - 8 hearing schedules across those cases (some past, some future; mixed reminder_sent)

Safe to re-run: uses get_or_create throughout so nothing is duplicated.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from cases.models import CaseFile, Client, HearingSchedule

User = get_user_model()

NOW = timezone.now()


class Command(BaseCommand):
    help = "Seed demo data: 1 lawyer, 3 clients, 5 cases, 8 hearings."

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _ok(self, msg: str) -> None:
        self.stdout.write(self.style.SUCCESS(f"  ✓ {msg}"))

    def _skip(self, msg: str) -> None:
        self.stdout.write(self.style.WARNING(f"  – {msg} (already exists)"))

    # ------------------------------------------------------------------
    # handle
    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== seed_demo_data ===\n"))

        # ── 1. Lawyer user ─────────────────────────────────────────────
        self.stdout.write("Creating lawyer user …")
        lawyer, created = User.objects.get_or_create(
            username="demo_lawyer",
            defaults={"role": "lawyer", "email": "demo_lawyer@example.com"},
        )
        if created:
            lawyer.set_password("demo12345")
            lawyer.save()
            self._ok("Created user 'demo_lawyer'")
        else:
            self._skip("User 'demo_lawyer'")

        # ── 2. Clients ─────────────────────────────────────────────────
        self.stdout.write("\nCreating clients …")
        client_data = [
            {
                "full_name": "Alice Johnson",
                "email": "alice@example.com",
                "contact_info": "+1-555-0101",
            },
            {
                "full_name": "Bob Martinez",
                "email": "bob@example.com",
                "contact_info": "+1-555-0102",
            },
            {
                "full_name": "Carol Lee",
                "email": "carol@example.com",
                "contact_info": "+1-555-0103",
            },
        ]
        clients = []
        for cd in client_data:
            obj, created = Client.objects.get_or_create(
                email=cd["email"],
                lawyer=lawyer,
                defaults={
                    "full_name": cd["full_name"],
                    "contact_info": cd["contact_info"],
                },
            )
            clients.append(obj)
            if created:
                self._ok(f"Created client '{obj.full_name}'")
            else:
                self._skip(f"Client '{obj.full_name}'")

        alice, bob, carol = clients

        # ── 3. Case files ──────────────────────────────────────────────
        self.stdout.write("\nCreating case files …")
        case_data = [
            {
                "case_title": "Johnson v. Smith — Property Dispute",
                "case_type": "Civil",
                "status": CaseFile.Status.OPEN,
                "client": alice,
            },
            {
                "case_title": "Martinez — DUI Defence",
                "case_type": "Criminal",
                "status": CaseFile.Status.PENDING,
                "client": bob,
            },
            {
                "case_title": "Lee — Divorce Proceedings",
                "case_type": "Family",
                "status": CaseFile.Status.OPEN,
                "client": carol,
            },
            {
                "case_title": "Johnson — Workplace Injury Claim",
                "case_type": "Personal Injury",
                "status": CaseFile.Status.CLOSED,
                "client": alice,
            },
            {
                "case_title": "Martinez — Immigration Petition",
                "case_type": "Immigration",
                "status": CaseFile.Status.PENDING,
                "client": bob,
            },
        ]
        cases = []
        for cd in case_data:
            obj, created = CaseFile.objects.get_or_create(
                case_title=cd["case_title"],
                lawyer=lawyer,
                defaults={
                    "case_type": cd["case_type"],
                    "status": cd["status"],
                    "client": cd["client"],
                },
            )
            cases.append(obj)
            if created:
                self._ok(f"Created case '{obj.case_title}' [{obj.status}]")
            else:
                self._skip(f"Case '{obj.case_title}'")

        # ── 4. Hearing schedules ───────────────────────────────────────
        self.stdout.write("\nCreating hearing schedules …")

        # 8 hearings: mix of past / future and reminder_sent true / false
        hearing_data = [
            # Past hearings (reminder_sent should logically be True)
            {
                "case": cases[0],
                "hearing_date": NOW - timedelta(days=30),
                "description": "Initial case management conference",
                "reminder_sent": True,
            },
            {
                "case": cases[1],
                "hearing_date": NOW - timedelta(days=14),
                "description": "Bail hearing",
                "reminder_sent": True,
            },
            {
                "case": cases[3],
                "hearing_date": NOW - timedelta(days=60),
                "description": "Settlement conference — final",
                "reminder_sent": True,
            },
            {
                "case": cases[2],
                "hearing_date": NOW - timedelta(days=7),
                "description": "Preliminary hearing",
                "reminder_sent": False,   # reminder was missed
            },
            # Future hearings
            {
                "case": cases[0],
                "hearing_date": NOW + timedelta(days=10),
                "description": "Evidence submission deadline hearing",
                "reminder_sent": False,
            },
            {
                "case": cases[2],
                "hearing_date": NOW + timedelta(days=21),
                "description": "Mediation session",
                "reminder_sent": False,
            },
            {
                "case": cases[4],
                "hearing_date": NOW + timedelta(days=45),
                "description": "Status conference — immigration file",
                "reminder_sent": False,
            },
            {
                "case": cases[1],
                "hearing_date": NOW + timedelta(days=60),
                "description": "Trial commencement",
                "reminder_sent": True,   # reminder sent early
            },
        ]

        for hd in hearing_data:
            obj, created = HearingSchedule.objects.get_or_create(
                case=hd["case"],
                description=hd["description"],
                defaults={
                    "hearing_date": hd["hearing_date"],
                    "reminder_sent": hd["reminder_sent"],
                },
            )
            when = "past" if hd["hearing_date"] < NOW else "future"
            if created:
                self._ok(
                    f"Created hearing '{obj.description}' "
                    f"[{when}, reminder_sent={obj.reminder_sent}]"
                )
            else:
                self._skip(f"Hearing '{obj.description}'")

        # ── Summary ────────────────────────────────────────────────────
        self.stdout.write(
            self.style.SUCCESS(
                "\n=== Done! Demo data is ready. ===\n"
                f"  Lawyer   : demo_lawyer  (password: demo12345)\n"
                f"  Clients  : {Client.objects.filter(lawyer=lawyer).count()}\n"
                f"  Cases    : {CaseFile.objects.filter(lawyer=lawyer).count()}\n"
                f"  Hearings : {HearingSchedule.objects.filter(case__lawyer=lawyer).count()}\n"
            )
        )
