# DemoPort - 개발자 프로필 웹사이트

장경수의 개발자 포트폴리오 사이트입니다. 요구사항은 [prd.md](prd.md)를 따릅니다.
Django 5 + SQLite(개발) / PostgreSQL(운영) + Django Template + 순수 CSS/JS로 만들었습니다.

## 빠른 시작 (Windows PowerShell)

```powershell
cd C:\work\DemoPort
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt   # psycopg/gunicorn 설치가 실패하면 앞의 4개만 설치해도 됩니다
Copy-Item .env.example .env          # 필요하면 값 수정
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed_demo        # 시작용 콘텐츠 (선택)
.\.venv\Scripts\python manage.py createsuperuser  # 관리자 계정
.\.venv\Scripts\python manage.py runserver
```

- 사이트: http://127.0.0.1:8000/
- 관리자: http://127.0.0.1:8000/admin/ (`ADMIN_URL` 환경변수로 변경 가능)
- 테스트: `.\.venv\Scripts\python manage.py test`

> `seed_demo`가 넣는 소개·철학·프로젝트 설명은 시작용 초안입니다.
> 실제 경력, 프로젝트, 링크는 관리자 페이지에서 수정해 주세요.

## PRD 구현 현황

| PRD | 구현 위치 |
|---|---|
| 4.1 홈 (H-1~H-4) | `templates/portfolio/home.html`, 스크롤 등장 애니메이션은 `static/js/main.js` |
| 4.2 소개 (A-1~A-3) | `about.html` (개발 철학, 바이브코딩 작업 방식 섹션, 경력 타임라인) |
| 4.3 기술 스택 (S-1~S-3) | `skills.html` (주력 강조, 분류별 표시, 기술→프로젝트 링크) |
| 4.4 프로젝트 (P-1~P-4) | `project_list.html`(태그 필터), `project_detail.html`(AI 협업 과정 포함) |
| 4.5 연락처 (C-1~C-5) | `contact.html`, `forms.py`, `views.py` (서버 검증, honeypot, 빈도 제한, 알림 메일) |
| 4.6 관리자 (M-1~M-3) | `portfolio/admin.py` (콘텐츠 CRUD, 문의 읽음/처리 상태, 공개·대표·정렬) |
| 5 사이트 구조 | `config/urls.py`, `portfolio/urls.py`, `sitemap.xml`, `robots.txt` |
| 6.1 데이터 모델 | `portfolio/models.py` (인덱스 2개, 집계 쿼리는 `views.skills_with_counts`) |
| 7 비기능 | 아래 참고 |

**비기능 요구사항 대응**
- 성능: 업로드 이미지 WebP 변환·리사이즈(`images.py`), `loading="lazy"`, `prefetch_related`와 집계 쿼리(목록 쿼리 수가 프로젝트 수와 무관함을 테스트로 검증)
- 접근성: 시맨틱 HTML, 건너뛰기 링크, 키보드 포커스 표시, `aria-current`, 대체 텍스트, 명도 대비 고려
- SEO: 페이지별 title/description, Open Graph, canonical, JSON-LD, sitemap.xml, robots.txt
- 보안: CSRF, 비밀키·DB 정보 환경변수화, 관리자 URL 변경, 운영 시 HTTPS 리다이렉트/HSTS/보안 쿠키, IP는 해시로만 저장
- 반응형: 360px~1440px, 다크/라이트 테마 전환(OS 설정 자동 반영)

## 배포 (운영)

1. 환경변수를 설정합니다: `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`,
   `DJANGO_CSRF_TRUSTED_ORIGINS`, `SITE_URL`, `DATABASE_URL`(PostgreSQL), `ADMIN_URL`,
   메일 발송용 `EMAIL_*` (`.env.example` 참고)
2. `Procfile`(gunicorn)이 포함되어 있어 Render, Railway 등에서 그대로 사용할 수 있습니다.
   빌드 시 `pip install -r requirements.txt`, 배포 시 `migrate`, `collectstatic`이 실행됩니다.
3. 업로드 이미지(`media/`)는 영구 디스크가 필요합니다. 디스크를 붙였다면 `SERVE_MEDIA=True`로 Django가 직접 서비스하게 하거나,
   외부 스토리지(S3 등)로 교체하세요. 무료 플랜처럼 디스크가 초기화되는 환경에서는 이미지가 사라질 수 있습니다.
4. 리버스 프록시 뒤에서는 `X-Forwarded-For`의 첫 IP를 스팸 방지용 IP로 사용합니다.

## 폴더 구조

```
config/        프로젝트 설정 (settings, urls, wsgi)
portfolio/     앱 (models, views, forms, admin, sitemaps, tests, seed_demo 명령)
templates/     base.html, portfolio/*.html, 404/500, robots.txt
static/        css/style.css, js/main.js
```
