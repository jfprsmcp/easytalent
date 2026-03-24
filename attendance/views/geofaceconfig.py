from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.translation import gettext as __

from geofencing.models import GeoFencing
from facedetection.models import FaceDetection


def _get_company(request):
    try:
        return request.user.employee_get.get_company()
    except Exception:
        selected = request.session.get("selected_company")
        if selected and selected != "all":
            from base.models import Company
            return Company.objects.filter(id=selected).first()
    return None


def geofaceconfig(request):
    company = _get_company(request)

    geo = GeoFencing.objects.filter(company_id=company).first() if company else None
    face = FaceDetection.objects.filter(company_id=company).first() if company else None

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "geo":
            try:
                lat = float(request.POST.get("latitude", 0))
                lng = float(request.POST.get("longitude", 0))
                radius = int(request.POST.get("radius_in_meters", 100))
                start = "start" in request.POST

                if geo:
                    GeoFencing.objects.filter(id=geo.id).update(
                        latitude=lat, longitude=lng,
                        radius_in_meters=radius, start=start
                    )
                else:
                    GeoFencing.objects.create(
                        latitude=lat, longitude=lng,
                        radius_in_meters=radius, start=start,
                        company_id=company
                    )
                messages.success(request, __("Geocerca guardada exitosamente."))
            except Exception as e:
                messages.error(request, __("Error al guardar: ") + str(e))
            return redirect("geo-face-config")

        elif form_type == "face":
            start = "start" in request.POST
            if face:
                FaceDetection.objects.filter(id=face.id).update(start=start)
            else:
                FaceDetection.objects.create(company_id=company, start=start)
            messages.success(request, __("Detección facial guardada exitosamente."))
            return redirect("geo-face-config")

    context = {
        "geo_lat": str(geo.latitude) if geo else "",
        "geo_lng": str(geo.longitude) if geo else "",
        "geo_radius": geo.radius_in_meters if geo else 100,
        "geo_start": geo.start if geo else False,
        "face_start": face.start if face else False,
    }
    return render(request, "attendance/geofaceconfig/geo_face_config.html", context)
