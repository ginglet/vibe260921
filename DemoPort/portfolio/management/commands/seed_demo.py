"""초기 콘텐츠를 채운다. 이미 데이터가 있으면 건드리지 않는다.

여기 들어가는 소개·철학·프로젝트 설명은 시작용 초안이다.
실제 경력, 프로젝트, 링크는 관리자 페이지에서 직접 수정해 주세요.
"""
from django.core.management.base import BaseCommand

from portfolio.models import Profile, Project, Skill, SkillCategory

VIBE_APPROACH = """AI에게 작업을 맡기기 전에 요구사항과 수용 기준을 문서(PRD)로 먼저 정리합니다.

기능을 작은 단위로 나누어 생성하고, 매번 직접 실행하고 테스트한 뒤 커밋합니다.

AI가 만든 코드는 입력 검증, CSRF, SQL 인젝션 같은 보안 문제와 N+1 쿼리 같은 성능 문제를 사람이 직접 리뷰합니다.

주요 프롬프트와 의사결정은 기록해 두고, 다음 작업과 프로젝트 문서에 다시 활용합니다."""


class Command(BaseCommand):
    help = "포트폴리오 초기 데이터(프로필, 기술, 대표 프로젝트)를 생성합니다."

    def handle(self, *args, **options):
        if not Profile.objects.exists():
            Profile.objects.create(
                name="장경수",
                headline="바이브코딩으로 빠르게 만들고, Django와 SQL로 단단하게 다듬는 개발자",
                bio="바이브코딩, Django, SQL을 주력으로 웹 서비스를 만듭니다.\n"
                    "아이디어를 빠르게 동작하는 결과물로 옮기고, 데이터 설계와 검증으로 안정성을 챙기는 것을 좋아합니다.",
                philosophy="빠르게 만들되, 검증하고 이해한 코드만 남깁니다.\n"
                           "AI는 속도를 높여 주는 도구이고, 설계와 책임은 개발자에게 있다고 생각합니다.",
                vibe_coding_approach=VIBE_APPROACH,
                email="ginglet88@naver.com",
            )
            self.stdout.write("프로필을 생성했습니다.")

        if not SkillCategory.objects.exists():
            spec = [
                ("Backend", [("Python", False), ("Django", True)]),
                ("Database", [("SQL", True), ("SQLite", False), ("PostgreSQL", False)]),
                ("AI Tooling", [("바이브코딩", True)]),
                ("Frontend", [("HTML5", False), ("CSS3", False), ("JavaScript", False)]),
            ]
            for i, (cat_name, skills) in enumerate(spec):
                cat = SkillCategory.objects.create(name=cat_name, order=i)
                for j, (name, core) in enumerate(skills):
                    Skill.objects.create(category=cat, name=name, is_core=core, order=j)
            self.stdout.write("기술 목록을 생성했습니다.")

        if not Project.objects.exists():
            project = Project.objects.create(
                title="DemoPort",
                slug="demoport",
                summary="Django와 SQL로 만든 개발자 프로필 웹사이트 (바로 이 사이트)",
                description="작업물과 역량을 한곳에서 보여 주고, 프로젝트 문의를 웹 폼으로 받을 수 있는 개인 프로필 사이트가 필요했습니다.",
                role="기획, 설계, 개발 (바이브코딩)",
                solution="PRD를 먼저 작성한 뒤 Django 모델·Admin·템플릿으로 구현했습니다. "
                         "콘텐츠는 코드 수정 없이 Admin에서 관리하고, 문의는 DB에 저장합니다. "
                         "기술별 프로젝트 수는 집계 쿼리 한 번으로 가져오고, 문의 폼에는 honeypot과 요청 빈도 제한을 적용했습니다.",
                result="반응형 화면, 다크/라이트 테마, SEO(sitemap, Open Graph)를 갖춘 포트폴리오 사이트로 운영합니다.",
                ai_process="PRD의 요구사항을 기능 단위로 나누어 AI와 함께 구현했고, 각 단계마다 테스트를 실행해 검증했습니다.",
                is_featured=True,
                order=0,
            )
            project.skills.set(Skill.objects.filter(name__in=["Django", "SQL", "바이브코딩", "Python", "HTML5", "CSS3", "JavaScript"]))
            self.stdout.write("대표 프로젝트를 생성했습니다.")

        self.stdout.write(self.style.SUCCESS("완료. 관리자 페이지에서 내용을 실제 정보로 수정해 주세요."))
