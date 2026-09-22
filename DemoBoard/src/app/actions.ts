"use server";

import {
  addComment,
  createPost,
  deleteComment,
  deletePost,
  getPost,
  listPosts,
  updatePost,
  type ListParams,
  type ListResult,
} from "@/lib/db";
import { parseCommentForm, parsePostForm, parsePasswordOnly } from "@/lib/validation";
import { type Post, type PostSummary } from "@/lib/types";

export async function actionListPosts(
  params: ListParams,
): Promise<{ ok: true; result: ListResult } | { ok: false; error: string }> {
  try {
    const result = await listPosts(params);
    return { ok: true, result };
  } catch (error) {
    console.error("actionListPosts failed:", error);
    return { ok: false, error: "글 목록을 불러올 수 없습니다." };
  }
}

export async function actionGetPost(id: number): Promise<{ ok: true; post: Post } | { ok: false; error: string }> {
  try {
    const post = await getPost(id, { countView: true });
    if (!post) return { ok: false, error: "글을 찾을 수 없습니다." };
    return { ok: true, post };
  } catch (error) {
    console.error("actionGetPost failed:", error);
    return { ok: false, error: "글을 불러올 수 없습니다." };
  }
}

export async function actionCreatePost(formData: FormData): Promise<
  | { ok: true; postId: number }
  | { ok: false; error: string; values?: Record<string, string> }
> {
  try {
    const parsed = parsePostForm(formData);
    if (!parsed.ok) return { ok: false, error: "입력 값을 확인해 주세요.", values: parsed.values };
    const post = await createPost(parsed.data);
    return { ok: true, postId: post.id };
  } catch (error) {
    console.error("actionCreatePost failed:", error);
    return { ok: false, error: "글을 저장할 수 없습니다." };
  }
}

export async function actionUpdatePost(id: number, formData: FormData): Promise<
  | { ok: true }
  | { ok: false; error: string; values?: Record<string, string> }
> {
  try {
    const parsed = parsePostForm(formData);
    if (!parsed.ok) return { ok: false, error: "입력 값을 확인해 주세요.", values: parsed.values };
    const result = await updatePost(id, parsed.data);
    if (!result.ok) {
      if (result.error === "not_found") return { ok: false, error: "글을 찾을 수 없습니다." };
      return { ok: false, error: "비밀번호가 일치하지 않습니다." };
    }
    return { ok: true };
  } catch (error) {
    console.error("actionUpdatePost failed:", error);
    return { ok: false, error: "글을 수정할 수 없습니다." };
  }
}

export async function actionDeletePost(
  id: number,
  formData: FormData,
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    const password = parsePasswordOnly(formData);
    const result = await deletePost(id, password);
    if (!result.ok) {
      if (result.error === "not_found") return { ok: false, error: "글을 찾을 수 없습니다." };
      return { ok: false, error: "비밀번호가 일치하지 않습니다." };
    }
    return { ok: true };
  } catch (error) {
    console.error("actionDeletePost failed:", error);
    return { ok: false, error: "글을 삭제할 수 없습니다." };
  }
}

export async function actionAddComment(
  postId: number,
  formData: FormData,
): Promise<{ ok: true } | { ok: false; error: string; values?: Record<string, string> }> {
  try {
    const parsed = parseCommentForm(formData);
    if (!parsed.ok) return { ok: false, error: "입력 값을 확인해 주세요.", values: parsed.values };
    const result = await addComment(postId, parsed.data);
    if (!result.ok) return { ok: false, error: "글을 찾을 수 없습니다." };
    return { ok: true };
  } catch (error) {
    console.error("actionAddComment failed:", error);
    return { ok: false, error: "댓글을 저장할 수 없습니다." };
  }
}

export async function actionDeleteComment(
  postId: number,
  commentId: number,
  formData: FormData,
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    const password = parsePasswordOnly(formData);
    const result = await deleteComment(postId, commentId, password);
    if (!result.ok) {
      if (result.error === "not_found") return { ok: false, error: "댓글을 찾을 수 없습니다." };
      return { ok: false, error: "비밀번호가 일치하지 않습니다." };
    }
    return { ok: true };
  } catch (error) {
    console.error("actionDeleteComment failed:", error);
    return { ok: false, error: "댓글을 삭제할 수 없습니다." };
  }
}
