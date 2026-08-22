"""
Management command to seed the database with demonstration data.
Safe to run multiple times – uses get_or_create throughout.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from cases.models import CaseFile, Client, HearingSchedule


class Command(BaseCommand):
    help = "Seed the database with demo lawyer, clients, cases, and hearings."

    # ── colour helpers ──────────────────────────────────────────────
    def _created(self, label):
        self.stdout.write(self.style.SUCCESS(f"  ✓ Created {label}"))

    def _exists(self, label):
        self.stdout.write(self.style.WARNING(f"  – Already exists: {label}"))

    def _log(self, obj, label, created):
        if created:
            self._created(label)
        else:
            self._exists(label)

    # ── main ────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO("\n🌱 Seeding demo data …\n"))

        # ── 1. Lawyer user ──────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("▸ Lawyer"))
        lawyer, created = User.objects.get_or_create(
            username="demo_lawyer",
            defaults={
                "email": "demo_lawyer@legalapp.test",
                "role": "lawyer",
            },
        )
        if created:
            lawyer.set_password("demo12345")
            lawyer.save()
        self._log(lawyer, "demo_lawyer", created)

        # ── 2. Clients (3) ──────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("\n▸ Clients"))
        clients_data = [
            {
                "name": "Rahul Sharma",
                "email": "rahul.sharma@example.com",
                "phone": "+91-9876543210",
                "address": "42 MG Road, Bengaluru, Karnataka 560001",
            },
            {
                "name": "Priya Patel",
                "email": "priya.patel@example.com",
                "phone": "+91-9123456780",
                "address": "15 Connaught Place, New Delhi 110001",
            },
            {
                "name": "Amit Deshmukh",
                "email": "amit.deshmukh@example.com",
                "phone": "+91-9988776655",
                "address": "7 FC Road, Pune, Maharashtra 411004",
            },
        ]

        clients = []
        for cd in clients_data:
            client, created = Client.objects.get_or_create(
                lawyer=lawyer,
                name=cd["name"],
                defaults={
                    "email": cd["email"],
                    "phone": cd["phone"],
                    "address": cd["address"],
                },
            )
            self._log(client, cd["name"], created)
            clients.append(client)

        # ── 3. Case files (5) ───────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("\n▸ Case Files"))
        cases_data = [
            {
                "client": clients[0],
                "title": "Sharma vs. ABC Corp – Wrongful Termination",
                "description": "Employment dispute regarding wrongful termination without due process.",
                "status": "open",
                "citation_tags": "labour-law, wrongful-termination, industrial-disputes-act",
            },
            {
                "client": clients[0],
                "title": "Sharma Property Dispute – Plot No. 12",
                "description": "Land ownership dispute over inherited agricultural plot.",
                "status": "pending",
                "citation_tags": "property-law, inheritance, transfer-of-property-act",
            },
            {
                "client": clients[1],
                "title": "Patel vs. XYZ Insurance – Claim Rejection",
                "description": "Insurance claim rejected on grounds of alleged non-disclosure.",
                "status": "open",
                "citation_tags": "insurance-law, consumer-protection, IRDAI",
            },
            {
                "client": clients[1],
                "title": "Patel Divorce & Custody Settlement",
                "description": "Mutual consent divorce with child custody arrangement.",
                "status": "closed",
                "citation_tags": "family-law, divorce, custody, hindu-marriage-act",
            },
            {
                "client": clients[2],
                "title": "Deshmukh Startup IP Filing",
                "description": "Trademark registration and IP protection for a tech startup.",
                "status": "pending",
                "citation_tags": "IP-law, trademark, patents-act",
            },
        ]

        cases = []
        for cf in cases_data:
            case, created = CaseFile.objects.get_or_create(
                lawyer=lawyer,
                client=cf["client"],
                title=cf["title"],
                defaults={
                    "description": cf["description"],
                    "status": cf["status"],
                    "citation_tags": cf["citation_tags"],
                },
            )
            self._log(case, cf["title"], created)
            cases.append(case)

        # ── 4. Hearing schedules (8) ────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("\n▸ Hearing Schedules"))
        now = timezone.now()

        hearings_data = [
            # Past hearings
            {
                "case_file": cases[0],
                "hearing_date": now - timedelta(days=30),
                "description": "First hearing – framing of issues",
                "court_room": "Court Room 4, City Civil Court",
            },
            {
                "case_file": cases[0],
                "hearing_date": now - timedelta(days=10),
                "description": "Evidence submission by plaintiff",
                "court_room": "Court Room 4, City Civil Court",
            },
            {
                "case_file": cases[1],
                "hearing_date": now - timedelta(days=45),
                "description": "Preliminary hearing – title verification",
                "court_room": "Court Room 7, District Court",
            },
            {
                "case_file": cases[3],
                "hearing_date": now - timedelta(days=60),
                "description": "Final decree – mutual consent granted",
                "court_room": "Family Court, Room 2",
            },
            # Future hearings
            {
                "case_file": cases[0],
                "hearing_date": now + timedelta(days=15),
                "description": "Cross-examination of defendant witnesses",
                "court_room": "Court Room 4, City Civil Court",
            },
            {
                "case_file": cases[2],
                "hearing_date": now + timedelta(days=7),
                "description": "Consumer forum – first hearing on claim",
                "court_room": "Consumer Forum, Hall B",
            },
            {
                "case_file": cases[4],
                "hearing_date": now + timedelta(days=25),
                "description": "Trademark examination hearing",
                "court_room": "IP Office, Room 3",
            },
            {
                "case_file": cases[1],
                "hearing_date": now + timedelta(days=35),
                "description": "Survey report review & arguments",
                "court_room": "Court Room 7, District Court",
            },
        ]

        for hd in hearings_data:
            hearing, created = HearingSchedule.objects.get_or_create(
                case_file=hd["case_file"],
                description=hd["description"],
                defaults={
                    "hearing_date": hd["hearing_date"],
                    "court_room": hd["court_room"],
                },
            )
            self._log(hearing, hd["description"], created)

        self.stdout.write(self.style.SUCCESS("\n✅ Demo data seeding complete!\n"))
