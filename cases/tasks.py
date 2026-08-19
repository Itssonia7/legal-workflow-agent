from celery import shared_task
from django.db import transaction
from .models import HearingSchedule

@shared_task
def check_hearing_schedule_collision(hearing_id):
    """
    Checks if the lawyer associated with this hearing has any other hearings scheduled 
    at the exact same time.
    """
    try:
        hearing = HearingSchedule.objects.get(id=hearing_id)
    except HearingSchedule.DoesNotExist:
        return {"status": "error", "message": "Hearing not found."}

    lawyer = hearing.case_file.lawyer
    
    with transaction.atomic():
        # Search for other hearings for the same lawyer at the same time
        collisions = HearingSchedule.objects.filter(
            case_file__lawyer=lawyer,
            hearing_date=hearing.hearing_date
        ).exclude(id=hearing.id)

        if collisions.exists():
            # Mark current and all colliding hearings
            hearing.collision_warning = True
            hearing.save(update_fields=['collision_warning'])
            collisions.update(collision_warning=True)

            collision_details = []
            for c in collisions:
                collision_details.append(
                    f"Case '{c.case_file.title}' in Courtroom '{c.court_room}'"
                )
            
            warning_msg = f"[⚠️ Collision Alert] Date collision detected for Lawyer {lawyer.username}: {', '.join(collision_details)}"
            print(warning_msg)
            return {
                "status": "collision_detected",
                "message": warning_msg,
                "collisions": [c.id for c in collisions]
            }
        else:
            # Clear warning if no collision
            hearing.collision_warning = False
            hearing.save(update_fields=['collision_warning'])
            return {"status": "ok", "message": "No date collisions detected."}

