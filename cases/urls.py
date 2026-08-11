from rest_framework.routers import DefaultRouter

from .views import ClientViewSet, CaseFileViewSet, HearingScheduleViewSet

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'cases', CaseFileViewSet, basename='casefile')
router.register(r'hearings', HearingScheduleViewSet, basename='hearingschedule')

urlpatterns = router.urls
