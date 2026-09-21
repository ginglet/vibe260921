from django.conf import settings

from .models import Profile


def site(request):
    """모든 템플릿에서 프로필(푸터·헤더용)과 사이트 주소를 쓸 수 있게 한다."""
    return {
        "profile": Profile.objects.prefetch_related("links").first(),
        "SITE_URL": settings.SITE_URL,
    }
