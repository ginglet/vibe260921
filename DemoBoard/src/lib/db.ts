import { supabase } from "./supabase";
import { hashPassword, verifyPassword } from "./password";
import type {
  Category,
  CategoryInfo,
  Comment,
  Post,
  PostSummary,
} from "./types";

export const PAGE_SIZE = 10;

// ============ Types for Supabase rows ============

interface PostRow {
  id: number;
  title: string;
  content: string;
  author: string;
  category: Category;
  password_hash: string;
  views: number;
  created_at: string;
  updated_at: string;
  is_notice: boolean;
  comments?: CommentRow[];
  comments_count?: Array<{ count: number }>;
}

interface CommentRow {
  id: number;
  post_id: number;
  author: string;
  content: string;
  password_hash: string;
  created_at: string;
}

// ============ Helper functions ============

function toComment(row: CommentRow): Comment {
  return {
    id: row.id,
    author: row.author,
    content: row.content,
    createdAt: row.created_at,
  };
}

function toPost(row: PostRow): Post {
  return {
    id: row.id,
    title: row.title,
    content: row.content,
    author: row.author,
    category: row.category,
    views: row.views,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    comments: (row.comments || []).map(toComment),
  };
}

function toSummary(row: PostRow): PostSummary {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    category: row.category,
    views: row.views,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    commentCount: row.comments?.length || 0,
  };
}

// ============ Public API ============

export interface ListParams {
  q?: string;
  category?: Category;
  page?: number;
  pageSize?: number;
}

export interface ListResult {
  items: PostSummary[];
  total: number;
  page: number;
  totalPages: number;
}

export async function listPosts({ q, category, page = 1, pageSize = PAGE_SIZE }: ListParams): Promise<ListResult> {
  try {
    const keyword = q?.trim().toLowerCase();

    // Fetch all posts with comments count (simpler approach for demo)
    const { data: allPosts, error, count } = await supabase
      .from("posts")
      .select("id, title, author, category, views, created_at, updated_at, is_notice, comments(count)", {
        count: "exact",
      })
      .order("is_notice", { ascending: false })
      .order("created_at", { ascending: false });

    if (error) throw error;

    // Filter by category and search
    const filtered = (allPosts || [])
      .filter((p: any) => !category || p.category === category)
      .filter((p: any) => {
        if (!keyword) return true;
        return (
          p.title.toLowerCase().includes(keyword) ||
          p.author.toLowerCase().includes(keyword)
        );
      });

    // Paginate
    const total = count || 0;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    const current = Math.min(Math.max(1, page), totalPages);
    const start = (current - 1) * pageSize;
    const end = start + pageSize;

    const items = filtered.slice(start, end).map((p: any) => ({
      ...toSummary(p),
      commentCount: p.comments?.[0]?.count || 0,
    }));

    return { items, total, page: current, totalPages };
  } catch (error) {
    console.error("listPosts error:", error);
    throw error;
  }
}

/** Get single post with comments */
export async function getPost(id: number, { countView = false } = {}): Promise<Post | null> {
  try {
    if (countView) {
      // Increment views via RPC function
      const { error: rpcError } = await (supabase.rpc as any)("increment_post_views", {
        post_id: id,
      });
      if (rpcError) console.error("increment_post_views error:", rpcError);
    }

    // Fetch post with comments
    const { data, error } = await supabase
      .from("posts")
      .select("*, comments(*)")
      .eq("id", id)
      .single();

    if (error) {
      if (error.code === "PGRST116") return null; // No rows found
      throw error;
    }

    if (!data) return null;

    // Sort comments by created_at
    const typedData = data as any;
    if (typedData.comments) {
      typedData.comments.sort((a: CommentRow, b: CommentRow) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      );
    }

    return toPost(typedData as PostRow);
  } catch (error) {
    console.error("getPost error:", error);
    throw error;
  }
}

// ============ Categories ============

interface CategoryRow {
  id: number;
  name: string;
  sort_order: number;
  is_pinned: boolean;
}

function toCategory(row: CategoryRow): CategoryInfo {
  return { id: row.id, name: row.name, sortOrder: row.sort_order, isPinned: row.is_pinned };
}

export async function listCategories(): Promise<CategoryInfo[]> {
  const { data, error } = await supabase
    .from("categories")
    .select("*")
    .order("sort_order", { ascending: true })
    .order("id", { ascending: true });

  if (error) throw error;
  return (data || []).map((row: any) => toCategory(row as CategoryRow));
}

export type CategoryMutationError =
  | "not_found"
  | "duplicate_name"
  | "invalid_name"
  | "in_use";

export async function createCategory(
  name: string,
  isPinned = false,
): Promise<{ ok: true; category: CategoryInfo } | { ok: false; error: CategoryMutationError }> {
  const trimmed = name.trim();
  if (!trimmed) return { ok: false, error: "invalid_name" };

  try {
    const { data: maxRow } = await (supabase
      .from("categories")
      .select("sort_order")
      .order("sort_order", { ascending: false })
      .limit(1) as any)
      .maybeSingle();

    const nextSortOrder = (maxRow?.sort_order ?? -1) + 1;

    const { data, error } = await (supabase
      .from("categories")
      .insert({ name: trimmed, sort_order: nextSortOrder, is_pinned: isPinned })
      .select("*") as any)
      .single();

    if (error) {
      if (error.code === "23505") return { ok: false, error: "duplicate_name" };
      throw error;
    }

    return { ok: true, category: toCategory(data as CategoryRow) };
  } catch (error) {
    console.error("createCategory error:", error);
    throw error;
  }
}

export async function renameCategory(
  id: number,
  name: string,
): Promise<{ ok: true; category: CategoryInfo } | { ok: false; error: CategoryMutationError }> {
  const trimmed = name.trim();
  if (!trimmed) return { ok: false, error: "invalid_name" };

  try {
    const { data, error } = await (supabase
      .from("categories")
      .update({ name: trimmed })
      .eq("id", id)
      .select("*") as any)
      .single();

    if (error) {
      if (error.code === "23505") return { ok: false, error: "duplicate_name" };
      if (error.code === "PGRST116") return { ok: false, error: "not_found" };
      throw error;
    }
    if (!data) return { ok: false, error: "not_found" };

    return { ok: true, category: toCategory(data as CategoryRow) };
  } catch (error) {
    console.error("renameCategory error:", error);
    throw error;
  }
}

export async function setCategoryPinned(
  id: number,
  isPinned: boolean,
): Promise<{ ok: true; category: CategoryInfo } | { ok: false; error: CategoryMutationError }> {
  try {
    const { data, error } = await (supabase
      .from("categories")
      .update({ is_pinned: isPinned })
      .eq("id", id)
      .select("*") as any)
      .single();

    if (error) {
      if (error.code === "PGRST116") return { ok: false, error: "not_found" };
      throw error;
    }
    if (!data) return { ok: false, error: "not_found" };

    return { ok: true, category: toCategory(data as CategoryRow) };
  } catch (error) {
    console.error("setCategoryPinned error:", error);
    throw error;
  }
}

export async function deleteCategory(
  id: number,
): Promise<{ ok: true } | { ok: false; error: CategoryMutationError }> {
  try {
    const { error } = await supabase.from("categories").delete().eq("id", id);

    if (error) {
      // 이 카테고리를 사용 중인 글이 있으면 FK(on delete restrict)가 막는다.
      if (error.code === "23503") return { ok: false, error: "in_use" };
      throw error;
    }

    return { ok: true };
  } catch (error) {
    console.error("deleteCategory error:", error);
    throw error;
  }
}

export type MutationError = "not_found" | "wrong_password" | "invalid_category";

export interface NewPost {
  title: string;
  content: string;
  author: string;
  category: Category;
  password: string;
}

export async function createPost(input: NewPost): Promise<Post> {
  try {
    const now = new Date().toISOString();
    const { data, error } = await (supabase
      .from("posts")
      .insert({
        title: input.title,
        content: input.content,
        author: input.author,
        category: input.category,
        password_hash: hashPassword(input.password),
        views: 0,
        created_at: now,
        updated_at: now,
      })
      .select("*, comments(*)") as any)
      .single();

    if (error) throw error;
    if (!data) throw new Error("Failed to create post");

    return toPost(data as PostRow);
  } catch (error) {
    console.error("createPost error:", error);
    throw error;
  }
}

export async function updatePost(
  id: number,
  input: NewPost
): Promise<{ ok: true; post: Post } | { ok: false; error: MutationError }> {
  try {
    // Fetch existing post to verify password
    const { data: existing, error: fetchError } = await (supabase
      .from("posts")
      .select("password_hash")
      .eq("id", id) as any)
      .single();

    if (fetchError || !existing) return { ok: false, error: "not_found" };

    if (!verifyPassword(input.password, (existing as any).password_hash)) {
      return { ok: false, error: "wrong_password" };
    }

    // Update post
    const { data, error } = await (supabase
      .from("posts")
      .update({
        title: input.title,
        content: input.content,
        author: input.author,
        category: input.category,
        updated_at: new Date().toISOString(),
      })
      .eq("id", id)
      .select("*, comments(*)") as any)
      .single();

    if (error) throw error;
    if (!data) throw new Error("Failed to update post");

    return { ok: true, post: toPost(data as PostRow) };
  } catch (error) {
    console.error("updatePost error:", error);
    throw error;
  }
}

export async function deletePost(
  id: number,
  password: string
): Promise<{ ok: true } | { ok: false; error: MutationError }> {
  try {
    // Fetch post to verify password
    const { data: post, error: fetchError } = await (supabase
      .from("posts")
      .select("password_hash")
      .eq("id", id) as any)
      .single();

    if (fetchError || !post) return { ok: false, error: "not_found" };

    if (!verifyPassword(password, (post as any).password_hash)) {
      return { ok: false, error: "wrong_password" };
    }

    // Delete post (comments cascade delete automatically)
    const { error } = await supabase.from("posts").delete().eq("id", id);

    if (error) throw error;

    return { ok: true };
  } catch (error) {
    console.error("deletePost error:", error);
    throw error;
  }
}

export async function addComment(
  postId: number,
  input: { author: string; content: string; password: string }
): Promise<{ ok: true } | { ok: false; error: "not_found" }> {
  try {
    // Verify post exists
    const { data: post } = await (supabase
      .from("posts")
      .select("id")
      .eq("id", postId) as any)
      .single();

    if (!post) return { ok: false, error: "not_found" };

    // Insert comment
    const { error } = await (supabase.from("comments").insert({
      post_id: postId,
      author: input.author,
      content: input.content,
      password_hash: hashPassword(input.password),
      created_at: new Date().toISOString(),
    }) as any);

    if (error) throw error;

    return { ok: true };
  } catch (error) {
    console.error("addComment error:", error);
    throw error;
  }
}

/** 관리자 전용: 비밀번호 확인 없이 글 삭제 */
export async function adminDeletePost(id: number): Promise<{ ok: true } | { ok: false; error: MutationError }> {
  try {
    const { data: post, error: fetchError } = await (supabase
      .from("posts")
      .select("id")
      .eq("id", id) as any)
      .single();

    if (fetchError || !post) return { ok: false, error: "not_found" };

    const { error } = await supabase.from("posts").delete().eq("id", id);
    if (error) throw error;

    return { ok: true };
  } catch (error) {
    console.error("adminDeletePost error:", error);
    throw error;
  }
}

/** 관리자 전용: 비밀번호 확인 없이 댓글 삭제 */
export async function adminDeleteComment(
  postId: number,
  commentId: number
): Promise<{ ok: true } | { ok: false; error: MutationError }> {
  try {
    const { data: comment, error: fetchError } = await (supabase
      .from("comments")
      .select("id")
      .eq("id", commentId)
      .eq("post_id", postId) as any)
      .single();

    if (fetchError || !comment) return { ok: false, error: "not_found" };

    const { error } = await supabase
      .from("comments")
      .delete()
      .eq("id", commentId)
      .eq("post_id", postId);
    if (error) throw error;

    return { ok: true };
  } catch (error) {
    console.error("adminDeleteComment error:", error);
    throw error;
  }
}

export async function deleteComment(
  postId: number,
  commentId: number,
  password: string
): Promise<{ ok: true } | { ok: false; error: MutationError }> {
  try {
    // Fetch comment to verify password
    const { data: comment, error: fetchError } = await (supabase
      .from("comments")
      .select("password_hash, post_id")
      .eq("id", commentId)
      .eq("post_id", postId) as any)
      .single();

    if (fetchError || !comment) return { ok: false, error: "not_found" };

    if (!verifyPassword(password, (comment as any).password_hash)) {
      return { ok: false, error: "wrong_password" };
    }

    // Delete comment
    const { error } = await supabase
      .from("comments")
      .delete()
      .eq("id", commentId)
      .eq("post_id", postId);

    if (error) throw error;

    return { ok: true };
  } catch (error) {
    console.error("deleteComment error:", error);
    throw error;
  }
}
