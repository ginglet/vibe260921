// 카테고리 뱃지 색상. 고정(공지) 카테고리는 항상 테마의 primary(teal) 색을 쓰고,
// 나머지는 정렬 순서를 기준으로 고정 팔레트를 순환해서 배정한다.
const PALETTE = [
  { bg: "#EFEDFB", fg: "#6B5FD0" }, // indigo
  { bg: "#FBEEE4", fg: "#C25B23" }, // amber/orange
  { bg: "#E5F5EE", fg: "#2E8B6B" }, // green
  { bg: "#FBE7EE", fg: "#C43D74" }, // pink
  { bg: "#E7F1FB", fg: "#2A6FB0" }, // blue
];

export interface CategoryBadgeColor {
  bg: string;
  fg: string;
}

/** isPinned인 카테고리는 테마 accent(teal)를, 그 외에는 팔레트를 순환해서 반환한다. */
export function categoryBadgeColor(sortOrder: number, isPinned: boolean): CategoryBadgeColor {
  if (isPinned) {
    return { bg: "var(--accent)", fg: "var(--primary)" };
  }
  const palette = PALETTE[((sortOrder % PALETTE.length) + PALETTE.length) % PALETTE.length];
  return palette;
}
