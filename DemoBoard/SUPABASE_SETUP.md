# Supabase 설정 가이드

DemoBoard는 Supabase PostgreSQL을 사용합니다. 다음 단계를 따라 설정하세요.

## 1️⃣ Supabase 프로젝트 생성

1. [Supabase](https://app.supabase.com)에서 계정 생성 또는 로그인
2. **"New Project"** 클릭
3. 프로젝트명, 데이터베이스 비밀번호 설정 후 생성

## 2️⃣ 테이블 생성

1. **SQL Editor** 열기
2. 새 쿼리 생성 후 `supabase/schema.sql`의 **첫 번째 부분** 실행 (테이블 생성)
3. 같은 쿼리에서 **두 번째 부분** 실행 (시드 데이터 삽입)

**또는** [여기](./supabase/schema.sql)에서 전체 SQL을 복사해서 한 번에 실행하세요.

## 3️⃣ 환경 변수 설정

1. 프로젝트 **Settings** → **API** 열기
2. 다음 값 복사:
   - **Project URL** → `NEXT_PUBLIC_SUPABASE_URL`
   - **Service Role (secret)** → `SUPABASE_SERVICE_ROLE_KEY` (⚠️ 공개하지 마세요!)

3. 프로젝트 루트에 `.env.local` 파일 생성:
   ```bash
   cp .env.local.example .env.local
   ```

4. `.env.local`에 값 입력:
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
   ```

## 4️⃣ 개발 서버 실행

```bash
npm run dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000) 접속

## 📋 테이블 구조

### `posts` 테이블
- `id`: 자동 증가 ID
- `title`: 글 제목
- `content`: 글 내용
- `author`: 작성자
- `category`: 카테고리 (공지, 자유, 질문, 후기)
- `password_hash`: 비밀번호 (scrypt 해시)
- `views`: 조회수
- `created_at`: 작성일시
- `updated_at`: 수정일시
- `is_notice`: 공지사항 여부 (자동 계산)

### `comments` 테이블
- `id`: 자동 증가 ID
- `post_id`: 글 ID (외래키)
- `author`: 댓글 작성자
- `content`: 댓글 내용
- `password_hash`: 비밀번호 (scrypt 해시)
- `created_at`: 작성일시

## 🔐 보안

- ✅ Service Role Key는 **서버 전용** (`.env` 파일, 절대 클라이언트로 노출 금지)
- ✅ 비밀번호는 **scrypt 해싱** 저장
- ✅ RLS 활성화 (정책 없음 = 서버만 접근 가능)

## ⚠️ 주의사항

- `.env.local`은 `.gitignore`에 포함되어 있으므로 **커밋되지 않음**
- Service Role Key가 노출되면 즉시 Supabase 대시보드에서 재생성

## 🆘 문제 해결

**"Supabase environment variables not set" 에러**
- `.env.local` 파일이 존재하는지 확인
- 환경 변수 값이 올바르게 입력되었는지 확인
- 개발 서버 재시작 (`npm run dev`)

**"relation "public.posts" does not exist" 에러**
- SQL 스크립트를 Supabase SQL Editor에서 실행했는지 확인
- Table Editor에서 테이블이 보이는지 확인

---

설정 완료 후 [DemoBoard 사용](./README.md)을 참고하세요! 🎉
