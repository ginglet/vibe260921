// 카테고리는 이제 DB(`categories` 테이블)에서 관리자가 자유롭게 추가/수정/삭제한다.
// 실제로 존재하는 카테고리인지는 DB의 외래키 제약이 최종 검증한다.
export type Category = string;

export function isCategory(value: unknown): value is Category {
  return typeof value === "string" && value.trim().length > 0;
}

export interface CategoryInfo {
  id: number;
  name: string;
  sortOrder: number;
  isPinned: boolean;
}

// ============ Public API Types ============

export interface Comment {
  id: number;
  author: string;
  content: string;
  createdAt: string;
}

export interface Post {
  id: number;
  title: string;
  content: string;
  author: string;
  category: Category;
  views: number;
  createdAt: string;
  updatedAt: string;
  comments: Comment[];
}

export type PostSummary = Omit<Post, "content" | "comments"> & {
  commentCount: number;
};
