import tempfile
from datetime import date
from io import BytesIO

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from PIL import Image

from .models import ContactMessage, Experience, Profile, Project, Skill, SkillCategory


def make_profile():
    return Profile.objects.create(name="장경수", headline="테스트 소개", email="ginglet88@naver.com")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="demoport-test-media-"))
class ModelTests(TestCase):
    def test_skill_slug_auto_generated_and_unique(self):
        cat = SkillCategory.objects.create(name="Backend")
        a = Skill.objects.create(category=cat, name="Django")
        b = Skill.objects.create(category=cat, name="Django ")
        self.assertEqual(a.slug, "django")
        self.assertNotEqual(a.slug, b.slug)

    def test_korean_skill_slug(self):
        cat = SkillCategory.objects.create(name="AI")
        self.assertEqual(Skill.objects.create(category=cat, name="바이브코딩").slug, "바이브코딩")

    def test_uploaded_image_converted_to_webp(self):
        buf = BytesIO()
        Image.new("RGB", (2400, 1200), "red").save(buf, "PNG")
        p = Project.objects.create(
            title="x", slug="x", summary="s", description="d",
            thumbnail=SimpleUploadedFile("shot.png", buf.getvalue(), content_type="image/png"),
        )
        self.assertTrue(p.thumbnail.name.endswith(".webp"))
        self.assertLessEqual(Image.open(p.thumbnail.path).width, 1200)


class PublicPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_profile()
        cat = SkillCategory.objects.create(name="Backend")
        cls.django = Skill.objects.create(category=cat, name="Django", is_core=True)
        cls.sql = Skill.objects.create(category=cat, name="SQL", is_core=True)
        cls.pub = Project.objects.create(title="공개 프로젝트", slug="pub", summary="요약", description="설명",
                                         is_featured=True, order=1)
        cls.pub.skills.add(cls.django)
        cls.hidden = Project.objects.create(title="비공개 프로젝트", slug="hidden", summary="숨김", description="설명",
                                            is_published=False)
        cls.hidden.skills.add(cls.sql)
        Experience.objects.create(kind="career", title="개발자", organization="회사", start_date=date(2024, 1, 1))

    def test_all_public_pages_ok(self):
        for name in ["home", "about", "skills", "project_list", "contact"]:
            res = self.client.get(reverse(f"portfolio:{name}"))
            self.assertEqual(res.status_code, 200, name)

    def test_home_shows_name_stack_and_featured(self):
        res = self.client.get(reverse("portfolio:home"))
        self.assertContains(res, "장경수")
        self.assertContains(res, "프로젝트 보기")
        self.assertContains(res, "문의하기")
        self.assertContains(res, "공개 프로젝트")
        self.assertNotContains(res, "비공개 프로젝트")

    def test_hidden_project_not_listed_and_404(self):
        self.assertNotContains(self.client.get(reverse("portfolio:project_list")), "비공개 프로젝트")
        self.assertEqual(self.client.get(reverse("portfolio:project_detail", args=["hidden"])).status_code, 404)

    def test_project_detail(self):
        res = self.client.get(reverse("portfolio:project_detail", args=["pub"]))
        self.assertContains(res, "공개 프로젝트")
        self.assertContains(res, 'property="og:title"')

    def test_tag_filter(self):
        Project.objects.create(title="다른 프로젝트", slug="other", summary="o", description="d")
        res = self.client.get(reverse("portfolio:project_list"), {"tag": "django"})
        self.assertContains(res, "공개 프로젝트")
        self.assertNotContains(res, "다른 프로젝트")

    def test_skills_counts_only_published(self):
        res = self.client.get(reverse("portfolio:skills"))
        skills = {s.name: s.project_count for s in res.context["core_skills"]}
        self.assertEqual(skills, {"Django": 1, "SQL": 0})

    def test_about_experience_timeline(self):
        self.assertContains(self.client.get(reverse("portfolio:about")), "2024.01")

    def test_project_list_query_count_does_not_grow_with_projects(self):
        def queries():
            with CaptureQueriesContext(connection) as ctx:
                self.client.get(reverse("portfolio:project_list"))
            return len(ctx)

        before = queries()
        for i in range(6):
            p = Project.objects.create(title=f"p{i}", slug=f"p{i}", summary="s", description="d")
            p.skills.add(self.django)
        self.assertEqual(queries(), before)

    def test_404_page(self):
        res = self.client.get("/does-not-exist/")
        self.assertEqual(res.status_code, 404)
        self.assertContains(res, "페이지를 찾을 수 없습니다", status_code=404)

    def test_seo_endpoints(self):
        sm = self.client.get("/sitemap.xml")
        self.assertContains(sm, "/projects/pub/")
        self.assertNotContains(sm, "/projects/hidden/")
        self.assertContains(self.client.get("/robots.txt"), "Sitemap:")


@override_settings(CONTACT_NOTIFY_EMAIL="owner@example.com", CONTACT_RATE_LIMIT=3)
class ContactTests(TestCase):
    url = "/contact/"
    valid = {"name": "김방문", "email": "visitor@example.com", "subject": "협업 제안", "message": "안녕하세요, 프로젝트 문의드립니다.", "website": ""}

    def setUp(self):
        make_profile()

    def test_valid_submission_saved_and_notified(self):
        res = self.client.post(self.url, self.valid, follow=True)
        self.assertContains(res, "문의가 접수되었습니다")
        msg = ContactMessage.objects.get()
        self.assertEqual((msg.name, msg.is_read, msg.is_done), ("김방문", False, False))
        self.assertTrue(msg.ip_hash)
        self.assertNotIn("127.0.0.1", msg.ip_hash)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["owner@example.com"])

    def test_invalid_email_and_required_validated_on_server(self):
        res = self.client.post(self.url, {**self.valid, "email": "not-an-email", "name": ""})
        self.assertEqual(res.status_code, 400)
        self.assertContains(res, "올바른 이메일 형식이 아닙니다", status_code=400)
        self.assertContains(res, "이름을 입력해 주세요", status_code=400)
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_short_message_rejected(self):
        res = self.client.post(self.url, {**self.valid, "message": "짧음"})
        self.assertContains(res, "10자 이상", status_code=400)

    def test_honeypot_discards_silently(self):
        res = self.client.post(self.url, {**self.valid, "website": "http://spam.example"}, follow=True)
        self.assertContains(res, "문의가 접수되었습니다")
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_rate_limit(self):
        for _ in range(3):
            self.client.post(self.url, self.valid)
        res = self.client.post(self.url, self.valid)
        self.assertEqual(res.status_code, 429)
        self.assertEqual(ContactMessage.objects.count(), 3)

    def test_mail_failure_does_not_break_submission(self):
        with override_settings(EMAIL_BACKEND="portfolio.tests.BrokenBackend"):
            res = self.client.post(self.url, self.valid, follow=True)
        self.assertContains(res, "문의가 접수되었습니다")
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_page_shows_mailto_and_privacy_notice(self):
        res = self.client.get(self.url)
        self.assertContains(res, "mailto:ginglet88@naver.com")
        self.assertContains(res, "문의 응대 목적")


from django.core.mail.backends.base import BaseEmailBackend  # noqa: E402


class BrokenBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        raise RuntimeError("smtp down")


class AdminTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.admin = get_user_model().objects.create_superuser("root", "r@example.com", "pw-12345-x")
        self.client.force_login(self.admin)

    def test_admin_pages_load(self):
        make_profile()
        for model in ["profile", "skillcategory", "skill", "project", "experience", "contactmessage"]:
            res = self.client.get(f"/admin/portfolio/{model}/")
            self.assertEqual(res.status_code, 200, model)

    def test_profile_is_singleton(self):
        self.assertEqual(self.client.get("/admin/portfolio/profile/add/").status_code, 200)
        make_profile()
        self.assertEqual(self.client.get("/admin/portfolio/profile/add/").status_code, 403)

    def test_opening_message_marks_read(self):
        msg = ContactMessage.objects.create(name="a", email="a@b.co", subject="s", message="m" * 12)
        self.client.get(f"/admin/portfolio/contactmessage/{msg.pk}/change/")
        msg.refresh_from_db()
        self.assertTrue(msg.is_read)
