from django.contrib import admin

from .models import (
    ContactMessage, Experience, Profile, ProfileLink, Project, ProjectImage, Skill, SkillCategory,
)

admin.site.site_header = "DemoPort 관리"
admin.site.site_title = "DemoPort 관리"
admin.site.index_title = "콘텐츠 관리"


class ProfileLinkInline(admin.TabularInline):
    model = ProfileLink
    extra = 1


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "headline", "email")
    inlines = [ProfileLinkInline]
    fieldsets = (
        ("기본 정보", {"fields": ("name", "headline", "photo", "email", "github_url")}),
        ("소개", {"fields": ("bio", "philosophy", "vibe_coding_approach")}),
    )

    def has_add_permission(self, request):
        return not Profile.objects.exists()       # 프로필은 한 건만 둔다


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 1
    fields = ("name", "slug", "level", "is_core", "order")


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    list_editable = ("order",)
    inlines = [SkillInline]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_core", "level", "order")
    list_editable = ("is_core", "level", "order")
    list_filter = ("category", "is_core")
    search_fields = ("name",)


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


@admin.action(description="선택한 프로젝트를 공개")
def publish(modeladmin, request, queryset):
    queryset.update(is_published=True)


@admin.action(description="선택한 프로젝트를 비공개")
def unpublish(modeladmin, request, queryset):
    queryset.update(is_published=False)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "is_featured", "order", "created_at")
    list_editable = ("is_published", "is_featured", "order")
    list_filter = ("is_published", "is_featured", "skills")
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("skills",)
    inlines = [ProjectImageInline]
    actions = [publish, unpublish]
    fieldsets = (
        ("기본", {"fields": ("title", "slug", "summary", "thumbnail", "skills")}),
        ("내용", {"fields": ("description", "role", "solution", "result", "ai_process")}),
        ("링크", {"fields": ("demo_url", "repo_url")}),
        ("공개 설정", {"fields": ("is_published", "is_featured", "order")}),
    )


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "kind", "start_date", "end_date")
    list_filter = ("kind",)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "email", "subject", "is_read", "is_done")
    list_filter = ("is_read", "is_done")
    list_editable = ("is_done",)
    search_fields = ("name", "email", "subject", "message")
    date_hierarchy = "created_at"
    readonly_fields = ("name", "email", "subject", "message", "created_at", "ip_hash")
    fields = ("name", "email", "subject", "message", "created_at", "is_read", "is_done", "ip_hash")
    actions = ["mark_read", "mark_unread", "mark_done"]

    def has_add_permission(self, request):
        return False

    def change_view(self, request, object_id, form_url="", extra_context=None):
        # 상세 화면을 여는 순간 읽음 처리
        ContactMessage.objects.filter(pk=object_id, is_read=False).update(is_read=True)
        return super().change_view(request, object_id, form_url, extra_context)

    @admin.action(description="선택한 문의를 읽음으로 표시")
    def mark_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description="선택한 문의를 읽지 않음으로 표시")
    def mark_unread(self, request, queryset):
        queryset.update(is_read=False)

    @admin.action(description="선택한 문의를 처리 완료로 표시")
    def mark_done(self, request, queryset):
        queryset.update(is_read=True, is_done=True)
