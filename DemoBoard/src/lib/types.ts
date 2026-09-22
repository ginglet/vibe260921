export const CATEGORIES = ["공지", "자유", "질문", "후기"] as const;
export type Category = (typeof CATEGORIES)[number];

export function isCategory(value: unknown): value is Category {
  return typeof value === "string" && (CATEGORIES as readonly string[]).includes(value);
}

/** 파일에 저장되는 형태. passwordHash는 절대 클라이언트로 내보내지 않는다. */
export interface StoredComment {
  id: number;
  author: string;
  content: string;
  passwordHash: string;
  createdAt: string;
}

export interface StoredPost {
  id: number;
  title: string;
  content: string;
  author: string;
  category: Category;
  passwordHash: string;
  views: number;
  createdAt: string;
  updatedAt: string;
  comments: StoredComment[];
}

export interface Store {
  nextPostId: number;
  nextCommentId: number;
  posts: StoredPost[];
}

export type Comment = Omit<StoredComment, "passwordHash">;

export type Post = Omit<StoredPost, "passwordHash" | "comments"> & {
  comments: Comment[];
};

export type PostSummary = Omit<Post, "content" | "comments"> & {
  commentCount: number;
};
