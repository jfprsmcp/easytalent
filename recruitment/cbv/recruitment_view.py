"""
recruitment
"""

from typing import Any

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from recruitment.filters import RecruitmentFilter
from recruitment.forms import AddCandidateForm, RecruitmentCreationForm, SkillsForm
from recruitment.models import Candidate, Recruitment, Skill
from recruitment.views.linkedin import delete_post, post_recruitment_in_linkedin


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="recruitment.view_recruitment"), name="dispatch"
)
class RecruitmentView(TemplateView):
    """
    Recuitment page
    """

    template_name = "cbv/recruitment/recruitment.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="recruitment.view_recruitment"), name="dispatch"
)
class RecruitmentList(HorillaListView):
    """
    List view of recruitment
    """

    model = Recruitment
    filter_class = RecruitmentFilter
    view_id = "rec-view-container"

    bulk_update_fields = ["vacancy", "start_date", "end_date", "closed"]

    template_name = "cbv/recruitment/rec_main.html"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("list-recruitment")

    def get_queryset(self, queryset=None, filtered=False, *args, **kwargs):
        self.queryset = (
            super()
            .get_queryset(queryset, filtered, *args, **kwargs)
            .filter(is_active=self.request.GET.get("is_active", True))
        )
        return self.queryset

    columns = [
        (_("Reclutamiento"), "recruitment_column"),
        (_("Managers"), "managers_column"),
        (_("Puestos Abiertos"), "open_job_col"),
        (_("Vacantes"), "vacancy"),
        (_("Total Contratados"), "tot_hires"),
        (_("Fecha Inicio"), "start_date"),
        (_("Fecha Fin"), "end_date"),
        (_("Estado"), "status_col"),
    ]
    action_method = "rec_actions"

    header_attrs = {
        "recruitment_column": """
                                style="width : 200px !important"
                               """
    }

    row_status_indications = [
        (
            "closed--dot",
            _("Closed"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=closed]').val('true');
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "open--dot",
            _("Open"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=closed]').val('false');
                $('#applyFilter').click();

            "
            """,
        ),
    ]

    row_status_class = "closed-{closed}"

    sortby_mapping = [
        (_("Reclutamiento"), "recruitment_column"),
        (_("Vacantes"), "vacancy"),
        (_("Fecha Inicio"), "start_date"),
        (_("Fecha Fin"), "end_date"),
    ]

    row_attrs = """
                class="oh-permission-table--collapsed"
                hx-get='{recruitment_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="recruitment.view_recruitment"), name="dispatch"
)
class RecruitmentNav(HorillaNavView):
    """
    For nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("list-recruitment")

        self.create_attrs = f"""
                            hx-get='{reverse_lazy('recruitment-create')}'
                            hx-target="#genericModalBody"
                            data-target="#genericModal"
                            data-toggle="oh-modal-toggle"
                            """

    nav_title = _("Reclutamiento")
    filter_instance = RecruitmentFilter()
    filter_form_context_name = "form"
    search_swap_target = "#listContainer"
    filter_body_template = "cbv/recruitment/filters.html"


class RecruitmentCreationFormExtended(RecruitmentCreationForm):
    """
    extended form view for create
    """

    cols = {
        "title": 12,
        "description": 12,
        "is_published": 4,
        "optional_profile_image": 4,
        "optional_resume": 4,
    }

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Recruitment
        fields = [
            "title",
            "description",
            "open_positions",
            "recruitment_managers",
            "start_date",
            "end_date",
            "vacancy",
            "company_id",
            "survey_templates",
            "skills",
            "is_published",
            "optional_profile_image",
            "optional_resume",
            "publish_in_linkedin",
            "linkedin_account_id",
        ]
        exclude = ["is_active"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"data-summernote": ""}),
        }
        labels = {
            "title": _("Título"),
            "description": _("Descripción"),
            "start_date": _("Fecha de Inicio"),
            "end_date": _("Fecha de Fin"),
            "survey_templates": _("Plantillas de Encuesta"),
            "is_published": _("¿Publicado?"),
            "vacancy": _("Vacantes"),
            "open_positions": _("Puesto de Trabajo"),
            "recruitment_managers": _("Managers"),
            "company_id": _("Empresa"),
            "skills": _("Habilidades"),
            "optional_profile_image": _("¿Foto de perfil opcional?"),
            "optional_resume": _("¿CV opcional?"),
            "publish_in_linkedin": _("Publicar en LinkedIn"),
            "linkedin_account_id": _("Cuenta de LinkedIn"),
        }


class RecruitmentNewSkillForm(HorillaFormView):
    """
    form view for add new skill
    """

    model = Skill
    form_class = SkillsForm
    new_display_title = _("Skills")
    is_dynamic_create_view = True

    def form_valid(self, form: SkillsForm) -> HttpResponse:
        if form.is_valid():
            message = _("Nueva habilidad creada exitosamente")
            form.save()
            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="recruitment.view_recruitment"), name="dispatch"
)
class RecruitmentForm(HorillaFormView):
    """
    Form View
    """

    model = Recruitment
    form_class = RecruitmentCreationFormExtended
    new_display_title = _("Nuevo Reclutamiento")
    dynamic_create_fields = [("skills", RecruitmentNewSkillForm)]
    template_name = "cbv/recruitment/recruitment_form.html"

    def get_context_data(self, **kwargs):
        """
        Return context data with optional verbose name for form based on instance state.
        """
        context = super().get_context_data(**kwargs)

        if self.form.instance.pk:
            self.form_class.verbose_name = _("Editar Reclutamiento")
        return context

    def form_valid(self, form: RecruitmentCreationFormExtended) -> HttpResponse:
        """
        Process form submission to save or update a Recruitment object and display success message.
        """
        if form.is_valid():
            if form.instance.pk:
                recruitment = form.save()
                recruitment_managers = self.request.POST.getlist("recruitment_managers")
                if recruitment_managers:
                    recruitment.recruitment_managers.set(recruitment_managers)
                if recruitment.publish_in_linkedin and recruitment.linkedin_account_id:
                    delete_post(recruitment)
                    post_recruitment_in_linkedin(
                        self.request, recruitment, recruitment.linkedin_account_id
                    )
                message = _("Reclutamiento actualizado exitosamente")
            else:
                recruitment = form.save()
                recruitment_managers = self.request.POST.getlist("recruitment_managers")
                if recruitment_managers:
                    recruitment.recruitment_managers.set(recruitment_managers)
                if recruitment.publish_in_linkedin and recruitment.linkedin_account_id:
                    post_recruitment_in_linkedin(
                        self.request, recruitment, recruitment.linkedin_account_id
                    )
                message = _("Reclutamiento creado exitosamente")
            messages.success(self.request, message)
            if self.request.GET.get("pipeline") == "true":
                return HttpResponse("<script>window.location.reload();</script>")
            return self.HttpResponse()
        return super().form_valid(form)


class AddCandidateFormView(HorillaFormView):
    """
    form view for add candidate
    """

    form_class = AddCandidateForm
    model = Candidate
    new_display_title = _("Agregar Candidato")

    def get_initial(self) -> dict:
        initial = super().get_initial()
        stage_id = self.request.GET.get("stage_id")
        rec_id = self.request.GET.get("rec_id")
        initial["stage_id"] = stage_id
        initial["rec_id"] = rec_id
        return initial

    def form_valid(self, form: AddCandidateForm) -> HttpResponse:
        if form.is_valid():
            message = _("Candidato agregado exitosamente.")
            form.save()
            messages.success(self.request, message)
            return self.HttpResponse("<script>window.location.reload</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="recruitment.view_recruitment"), name="dispatch"
)
class RecruitmentFormDuplicate(HorillaFormView):
    """
    Duplicate form view
    """

    model = Recruitment
    form_class = RecruitmentCreationFormExtended

    def get_context_data(self, **kwargs):
        """
        Return context data for duplicating a Recruitment object form with modified initial values.
        """
        context = super().get_context_data(**kwargs)
        original_object = Recruitment.objects.get(id=self.kwargs["pk"])
        form = self.form_class(instance=original_object)
        for field_name, field in form.fields.items():
            if isinstance(field, forms.CharField):
                if field.initial:
                    initial_value = field.initial
                else:
                    initial_value = f"{form.initial.get(field_name, '')} (copia)"
                form.initial[field_name] = initial_value
                form.fields[field_name].initial = initial_value
        context["form"] = form
        self.form_class.verbose_name = _("Duplicar")
        return context

    def form_valid(self, form: RecruitmentCreationFormExtended) -> HttpResponse:
        """
        Process form submission to add a new recruitment.
        """
        form = self.form_class(self.request.POST)
        if form.is_valid():
            recruitment = form.save()
            message = _("Reclutamiento agregado exitosamente")
            recruitment.save()
            recruitment_managers = self.request.POST.getlist("recruitment_managers")
            job_positions = self.request.POST.getlist("open_positions")
            if recruitment_managers:
                recruitment.recruitment_managers.set(recruitment_managers)
            if job_positions:
                recruitment.open_positions.set(job_positions)
            messages.success(self.request, message)
            return self.HttpResponse()

        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="recruitment.view_recruitment"), name="dispatch"
)
class RecruitmentDetailView(HorillaDetailedView):
    """
    detail view of page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.body = [
            (_("Managers"), "managers_detail"),
            (_("Puestos Abiertos"), "open_job_detail"),
            (_("Vacantes"), "vacancy"),
            (_("Total Contratados"), "tot_hires"),
            (_("Fecha Inicio"), "start_date"),
            (_("Fecha Fin"), "end_date"),
        ]

    action_method = "detail_actions"

    model = Recruitment
    title = _("Detalles")
    header = {
        "title": "title",
        "subtitle": "status_col",
        "avatar": "get_avatar",
    }
