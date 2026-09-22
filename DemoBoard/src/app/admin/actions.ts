"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import {
  adminDeleteComment,
  adminDeletePost,
  createCategory,
  deleteCategory,
  renameCategory,
  setCategoryPinned,
  type CategoryMutationError,
} from "@/lib/db";
import type { CategoryInfo } from "@/lib/types";
import {
  ADMIN_COOKIE_NAME,
  ADMIN_SESSION_TTL_MS,
  checkAdminPassword,
  createSessionToken,
  isAdmin,
} from "@/lib/admin";

export interface AdminLoginState {
  error?: string;
}

export async function actionAdminLogin(
  _prevState: AdminLoginState | undefined,
  formData: FormData,
): Promise<AdminLoginState> {
  const password = String(formData.get("password") || "");

  if (!password || !checkAdminPassword(password)) {
    return { error: "비밀번호가 올바르지 않습니다." };
  }

  const cookieStore = await cookies();
  cookieStore.set(ADMIN_COOKIE_NAME, createSessionToken(), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: Math.floor(ADMIN_SESSION_TTL_MS / 1000),
  });

  redirect("/admin");
}

export async function actionAdminLogout(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(ADMIN_COOKIE_NAME);
  redirect("/admin/login");
}

export async function actionAdminDeletePost(
  id: number,
): Promise<{ ok: true } | { ok: false; error: string }> {
  if (!(await isAdmin())) return { ok: false, error: "권한이 없습니다." };

  try {
    const result = await adminDeletePost(id);
    if (!result.ok) return { ok: false, error: "글을 찾을 수 없습니다." };
    return { ok: true };
  } catch (error) {
    console.error("actionAdminDeletePost failed:", error);
    return { ok: false, error: "글을 삭제할 수 없습니다." };
  }
}

const CATEGORY_ERROR_MESSAGES: Record<CategoryMutationError, string> = {
  not_found: "카테고리를 찾을 수 없습니다.",
  duplicate_name: "이미 존재하는 카테고리 이름입니다.",
  invalid_name: "카테고리 이름을 입력해 주세요.",
  in_use: "이 카테고리를 사용 중인 글이 있어 삭제할 수 없습니다.",
};

export async function actionAdminCreateCategory(
  name: string,
): Promise<{ ok: true; category: CategoryInfo } | { ok: false; error: string }> {
  if (!(await isAdmin())) return { ok: false, error: "권한이 없습니다." };

  try {
    const result = await createCategory(name);
    if (!result.ok) return { ok: false, error: CATEGORY_ERROR_MESSAGES[result.error] };
    return { ok: true, category: result.category };
  } catch (error) {
    console.error("actionAdminCreateCategory failed:", error);
    return { ok: false, error: "카테고리를 추가할 수 없습니다." };
  }
}

export async function actionAdminRenameCategory(
  id: number,
  name: string,
): Promise<{ ok: true; category: CategoryInfo } | { ok: false; error: string }> {
  if (!(await isAdmin())) return { ok: false, error: "권한이 없습니다." };

  try {
    const result = await renameCategory(id, name);
    if (!result.ok) return { ok: false, error: CATEGORY_ERROR_MESSAGES[result.error] };
    return { ok: true, category: result.category };
  } catch (error) {
    console.error("actionAdminRenameCategory failed:", error);
    return { ok: false, error: "카테고리 이름을 바꿀 수 없습니다." };
  }
}

export async function actionAdminSetCategoryPinned(
  id: number,
  isPinned: boolean,
): Promise<{ ok: true; category: CategoryInfo } | { ok: false; error: string }> {
  if (!(await isAdmin())) return { ok: false, error: "권한이 없습니다." };

  try {
    const result = await setCategoryPinned(id, isPinned);
    if (!result.ok) return { ok: false, error: CATEGORY_ERROR_MESSAGES[result.error] };
    return { ok: true, category: result.category };
  } catch (error) {
    console.error("actionAdminSetCategoryPinned failed:", error);
    return { ok: false, error: "카테고리 설정을 바꿀 수 없습니다." };
  }
}

export async function actionAdminDeleteCategory(
  id: number,
): Promise<{ ok: true } | { ok: false; error: string }> {
  if (!(await isAdmin())) return { ok: false, error: "권한이 없습니다." };

  try {
    const result = await deleteCategory(id);
    if (!result.ok) return { ok: false, error: CATEGORY_ERROR_MESSAGES[result.error] };
    return { ok: true };
  } catch (error) {
    console.error("actionAdminDeleteCategory failed:", error);
    return { ok: false, error: "카테고리를 삭제할 수 없습니다." };
  }
}

export async function actionAdminDeleteComment(
  postId: number,
  commentId: number,
): Promise<{ ok: true } | { ok: false; error: string }> {
  if (!(await isAdmin())) return { ok: false, error: "권한이 없습니다." };

  try {
    const result = await adminDeleteComment(postId, commentId);
    if (!result.ok) return { ok: false, error: "댓글을 찾을 수 없습니다." };
    return { ok: true };
  } catch (error) {
    console.error("actionAdminDeleteComment failed:", error);
    return { ok: false, error: "댓글을 삭제할 수 없습니다." };
  }
}
