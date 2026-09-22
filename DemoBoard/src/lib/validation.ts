import { isCategory, type Category } from "./types";

export const LIMITS = {
  title: 100,
  content: 10000,
  author: 20,
  comment: 1000,
  passwordMin: 4,
  passwordMax: 50,
} as const;

export type FieldErrors = Partial<
  Record<"title" | "content" | "author" | "category" | "password", string>
>;

export interface PostInput {
  title: string;
  content: string;
  author: string;
  category: Category;
  password: string;
}

function text(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value : "";
}

function checkPassword(password: string, errors: FieldErrors) {
  if (password.length < LIMITS.passwordMin || password.length > LIMITS.passwordMax) {
    errors.password = `비밀번호는 ${LIMITS.passwordMin}~${LIMITS.passwordMax}자로 입력해 주세요.`;
  }
}

/** 새 글 작성 / 수정 폼 검증. 작성자는 수정 시에도 그대로 받는다. */
export function parsePostForm(
  formData: FormData,
): { ok: true; data: PostInput } | { ok: false; errors: FieldErrors; values: Record<string, string> } {
  const title = text(formData, "title").trim();
  const content = text(formData, "content").trim();
  const author = text(formData, "author").trim();
  const category = text(formData, "category");
  const password = text(formData, "password");
  const errors: FieldErrors = {};

  if (!title) errors.title = "제목을 입력해 주세요.";
  else if (title.length > LIMITS.title) errors.title = `제목은 ${LIMITS.title}자 이하로 입력해 주세요.`;

  if (!content) errors.content = "내용을 입력해 주세요.";
  else if (content.length > LIMITS.content) errors.content = `내용은 ${LIMITS.content}자 이하로 입력해 주세요.`;

  if (!author) errors.author = "작성자를 입력해 주세요.";
  else if (author.length > LIMITS.author) errors.author = `작성자는 ${LIMITS.author}자 이하로 입력해 주세요.`;

  if (!isCategory(category)) errors.category = "카테고리를 선택해 주세요.";

  checkPassword(password, errors);

  if (Object.keys(errors).length > 0 || !isCategory(category)) {
    return { ok: false, errors, values: { title, content, author, category } };
  }
  return { ok: true, data: { title, content, author, category, password } };
}

export function parseCommentForm(
  formData: FormData,
): { ok: true; data: { author: string; content: string; password: string } } | { ok: false; errors: FieldErrors & { content?: string }; values: Record<string, string> } {
  const author = text(formData, "author").trim();
  const content = text(formData, "content").trim();
  const password = text(formData, "password");
  const errors: FieldErrors = {};

  if (!author) errors.author = "작성자를 입력해 주세요.";
  else if (author.length > LIMITS.author) errors.author = `작성자는 ${LIMITS.author}자 이하로 입력해 주세요.`;

  if (!content) errors.content = "댓글 내용을 입력해 주세요.";
  else if (content.length > LIMITS.comment) errors.content = `댓글은 ${LIMITS.comment}자 이하로 입력해 주세요.`;

  checkPassword(password, errors);

  if (Object.keys(errors).length > 0) {
    return { ok: false, errors, values: { author, content } };
  }
  return { ok: true, data: { author, content, password } };
}

export function parsePasswordOnly(formData: FormData): string {
  return text(formData, "password");
}
