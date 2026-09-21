from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from .images import optimize_image


class Profile(models.Model):
    """사이트 주인(개발자) 프로필. 한 건만 사용한다."""

    name = models.CharField("이름", max_length=50)
    headline = models.CharField("한 줄 소개", max_length=200)
    bio = models.TextField("소개글", blank=True)
    philosophy = models.TextField("개발 철학", blank=True)
    vibe_coding_approach = models.TextField(
        "바이브코딩 작업 방식", blank=True,
        help_text="AI와 협업하는 과정, 검증 방법, 강점을 적어 주세요. (소개 페이지 별도 섹션)",
    )
    photo = models.ImageField("프로필 사진", upload_to="profile/", blank=True)
    email = models.EmailField("이메일")
    github_url = models.URLField("GitHub", blank=True)

    class Meta:
        verbose_name = "프로필"
        verbose_name_plural = "프로필"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        optimize_image(self.photo, max_width=800)
        super().save(*args, **kwargs)


class ProfileLink(models.Model):
    """블로그, LinkedIn 등 추가 외부 링크."""

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="links")
    label = models.CharField("이름", max_length=50)
    url = models.URLField("주소")
    order = models.PositiveSmallIntegerField("정렬", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "외부 링크"
        verbose_name_plural = "외부 링크"

    def __str__(self):
        return self.label


class SkillCategory(models.Model):
    name = models.CharField("분류명", max_length=50)
    order = models.PositiveSmallIntegerField("정렬", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "기술 분류"
        verbose_name_plural = "기술 분류"

    def __str__(self):
        return self.name


class Skill(models.Model):
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name="skills", verbose_name="분류")
    name = models.CharField("기술명", max_length=50)
    slug = models.SlugField("슬러그", max_length=60, unique=True, allow_unicode=True, blank=True,
                            help_text="프로젝트 필터 주소(?tag=슬러그)에 쓰입니다. 비워 두면 자동 생성됩니다.")
    level = models.PositiveSmallIntegerField(
        "숙련도", default=0, choices=[(0, "표시 안 함")] + [(i, f"{i}/5") for i in range(1, 6)],
    )
    is_core = models.BooleanField("주력 분야", default=False)
    order = models.PositiveSmallIntegerField("정렬", default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "기술"
        verbose_name_plural = "기술"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or "skill"
            slug, n = base, 2
            while Skill.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)


class Project(models.Model):
    title = models.CharField("제목", max_length=120)
    slug = models.SlugField("슬러그", max_length=140, unique=True, allow_unicode=True)
    summary = models.CharField("한 줄 설명", max_length=200)
    description = models.TextField("배경 / 문제")
    role = models.CharField("역할", max_length=200, blank=True)
    solution = models.TextField("해결 방법", blank=True)
    result = models.TextField("결과", blank=True)
    ai_process = models.TextField(
        "AI 협업 과정", blank=True,
        help_text="바이브코딩으로 진행한 프로젝트라면 프롬프트 전략, 검증 방법 등을 적어 주세요.",
    )
    thumbnail = models.ImageField("썸네일", upload_to="projects/thumbs/", blank=True)
    demo_url = models.URLField("데모 링크", blank=True)
    repo_url = models.URLField("GitHub 링크", blank=True)
    skills = models.ManyToManyField(Skill, related_name="projects", blank=True, verbose_name="사용 기술")
    is_featured = models.BooleanField("대표 프로젝트", default=False)
    is_published = models.BooleanField("공개", default=True)
    order = models.PositiveSmallIntegerField("정렬", default=0, help_text="작을수록 먼저 표시됩니다.")
    created_at = models.DateTimeField("등록일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]
        indexes = [models.Index(fields=["is_published", "order"], name="project_pub_order_idx")]
        verbose_name = "프로젝트"
        verbose_name_plural = "프로젝트"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("portfolio:project_detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        optimize_image(self.thumbnail, max_width=1200)
        super().save(*args, **kwargs)


class ProjectImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField("스크린샷", upload_to="projects/shots/")
    caption = models.CharField("설명", max_length=200, blank=True)
    order = models.PositiveSmallIntegerField("정렬", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "스크린샷"
        verbose_name_plural = "스크린샷"

    def __str__(self):
        return self.caption or f"{self.project} #{self.pk}"

    def save(self, *args, **kwargs):
        optimize_image(self.image, max_width=1600)
        super().save(*args, **kwargs)


class Experience(models.Model):
    class Kind(models.TextChoices):
        CAREER = "career", "경력"
        EDUCATION = "education", "학력"
        ACTIVITY = "activity", "활동"

    kind = models.CharField("구분", max_length=10, choices=Kind.choices, default=Kind.CAREER)
    title = models.CharField("직함 / 과정", max_length=120)
    organization = models.CharField("기관", max_length=120, blank=True)
    start_date = models.DateField("시작일")
    end_date = models.DateField("종료일", null=True, blank=True, help_text="비워 두면 '현재'로 표시됩니다.")
    description = models.TextField("설명", blank=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "경력·학력·활동"
        verbose_name_plural = "경력·학력·활동"

    def __str__(self):
        return f"{self.title} ({self.organization})" if self.organization else self.title


class ContactMessage(models.Model):
    name = models.CharField("이름", max_length=50)
    email = models.EmailField("이메일")
    subject = models.CharField("제목", max_length=120)
    message = models.TextField("내용")
    created_at = models.DateTimeField("접수일", auto_now_add=True)
    is_read = models.BooleanField("읽음", default=False)
    is_done = models.BooleanField("처리 완료", default=False)
    ip_hash = models.CharField("IP 해시", max_length=64, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["ip_hash", "created_at"], name="contact_ip_created_idx")]
        verbose_name = "문의"
        verbose_name_plural = "문의"

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d}] {self.name} - {self.subject}"
