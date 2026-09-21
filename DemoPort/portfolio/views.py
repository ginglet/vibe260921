import hashlib
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponseServerError
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from .forms import ContactForm
from .models import ContactMessage, Experience, Project, Skill, SkillCategory

logger = logging.getLogger(__name__)


def published_projects():
    return Project.objects.filter(is_published=True).prefetch_related("skills")


def skills_with_counts():
    """기술별 '공개된 프로젝트 수'를 한 번의 집계 쿼리로 함께 가져온다."""
    return Skill.objects.annotate(
        project_count=Count("projects", filter=Q(projects__is_published=True), distinct=True)
    )


def home(request):
    context = {
        "featured": published_projects().filter(is_featured=True)[:3],
        "core_skills": Skill.objects.filter(is_core=True),
    }
    return render(request, "portfolio/home.html", context)


def about(request):
    experiences = {label: [] for _, label in Experience.Kind.choices}
    labels = dict(Experience.Kind.choices)
    for exp in Experience.objects.all():
        experiences[labels[exp.kind]].append(exp)
    return render(request, "portfolio/about.html", {
        "experience_groups": [(label, items) for label, items in experiences.items() if items],
    })


def skills(request):
    categories = SkillCategory.objects.prefetch_related(
        Prefetch("skills", queryset=skills_with_counts())
    )
    return render(request, "portfolio/skills.html", {
        "core_skills": skills_with_counts().filter(is_core=True),
        "categories": [c for c in categories if c.skills.all()],
    })


def project_list(request):
    tag = request.GET.get("tag", "").strip()
    projects = published_projects()
    active_skill = None
    if tag:
        active_skill = Skill.objects.filter(slug=tag).first()
        projects = projects.filter(skills__slug=tag)
    return render(request, "portfolio/project_list.html", {
        "projects": projects,
        "tags": skills_with_counts().filter(project_count__gt=0),
        "active_tag": tag,
        "active_skill": active_skill,
    })


def project_detail(request, slug):
    project = get_object_or_404(
        Project.objects.filter(is_published=True).prefetch_related("skills", "images"), slug=slug
    )
    return render(request, "portfolio/project_detail.html", {"project": project})


# ------------------------------------------------------------------ 문의
def page_not_found(request, exception=None):
    return render(request, "404.html", status=404)


def server_error(request):
    # DB 장애 상황일 수 있으므로 컨텍스트 프로세서(DB 조회)를 거치지 않고 렌더링한다
    return HttpResponseServerError(render_to_string("500.html"))


def client_ip(request):
    ip = request.META.get("REMOTE_ADDR", "")
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded and not settings.DEBUG:      # 리버스 프록시(Render 등) 뒤에서 실제 IP 사용
        ip = forwarded.split(",")[0].strip()
    return ip


def hash_ip(ip):
    return hashlib.sha256(f"{settings.SECRET_KEY}:{ip}".encode()).hexdigest()


def is_rate_limited(ip_hash):
    since = timezone.now() - timedelta(minutes=settings.CONTACT_RATE_WINDOW_MIN)
    recent = ContactMessage.objects.filter(ip_hash=ip_hash, created_at__gte=since).count()
    return recent >= settings.CONTACT_RATE_LIMIT


def notify_owner(msg):
    try:
        send_mail(
            subject=f"[DemoPort 문의] {msg.subject}",
            message=f"보낸 사람: {msg.name} <{msg.email}>\n접수: {msg.created_at:%Y-%m-%d %H:%M}\n\n{msg.message}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CONTACT_NOTIFY_EMAIL],
            fail_silently=False,
        )
    except Exception:       # 메일 발송 실패가 문의 접수 자체를 막으면 안 된다
        logger.exception("문의 알림 메일 발송에 실패했습니다.")


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            if form.cleaned_data["website"]:          # honeypot: 봇은 성공한 것처럼 돌려보낸다
                messages.success(request, "문의가 접수되었습니다. 확인 후 회신드리겠습니다.")
                return redirect("portfolio:contact")
            ip_hash = hash_ip(client_ip(request))
            if is_rate_limited(ip_hash):
                form.add_error(None, "짧은 시간에 너무 많은 문의가 접수되었습니다. 잠시 후 다시 시도해 주세요.")
                return render(request, "portfolio/contact.html", {"form": form}, status=429)
            msg = form.save(commit=False)
            msg.ip_hash = ip_hash
            msg.save()
            notify_owner(msg)
            messages.success(request, "문의가 접수되었습니다. 확인 후 회신드리겠습니다.")
            return redirect("portfolio:contact")
        return render(request, "portfolio/contact.html", {"form": form}, status=400)
    return render(request, "portfolio/contact.html", {"form": ContactForm()})
