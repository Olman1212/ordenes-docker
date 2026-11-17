from django.conf import settings


def api(request):
    return {"API_URL": settings.API_URL}
