"""블럭깨기(Breakout) 게임 - tkinter 전용, 외부 라이브러리 불필요.

조작법
  ← / → 또는 마우스 : 패들 이동
  스페이스 / 클릭    : 공 발사, 게임오버·클리어 후 다시 시작
  P                  : 일시정지 / 재개
  ESC                : 종료
"""
import math
import random
import tkinter as tk

WIDTH, HEIGHT = 640, 520
FPS_DELAY = 16  # ms (약 60fps)

PADDLE_W, PADDLE_H = 100, 14
PADDLE_Y = HEIGHT - 40
PADDLE_SPEED = 9

BALL_R = 8
BALL_START_SPEED = 5.0
BALL_MAX_SPEED = 10.0

BRICK_COLS = 10
BRICK_ROWS = 6
BRICK_W = WIDTH // BRICK_COLS
BRICK_H = 22
BRICK_TOP = 60
ROW_COLORS = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db", "#9b59b6"]
ROW_POINTS = [60, 50, 40, 30, 20, 10]

START_LIVES = 3


class Breakout:
    def __init__(self, root):
        self.root = root
        root.title("블럭깨기")
        root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                                bg="#111827", highlightthickness=0)
        self.canvas.pack()

        self.keys = set()
        root.bind("<KeyPress>", self.on_key_press)
        root.bind("<KeyRelease>", self.on_key_release)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", self.on_click)
        root.bind("<Escape>", lambda e: root.destroy())

        self.new_game()
        self.tick()

    # ---------- 게임 상태 ----------
    def new_game(self):
        self.score = 0
        self.lives = START_LIVES
        self.level = 1
        self.state = "ready"  # ready / playing / paused / gameover / win
        self.build_level()

    def build_level(self):
        self.canvas.delete("all")
        self.bricks = {}  # canvas id -> (row, x1, y1, x2, y2)
        for r in range(BRICK_ROWS):
            for c in range(BRICK_COLS):
                x1 = c * BRICK_W + 2
                y1 = BRICK_TOP + r * BRICK_H + 2
                x2 = (c + 1) * BRICK_W - 2
                y2 = BRICK_TOP + (r + 1) * BRICK_H - 2
                item = self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=ROW_COLORS[r], outline="")
                self.bricks[item] = (r, x1, y1, x2, y2)

        self.paddle_x = WIDTH / 2
        self.paddle = self.canvas.create_rectangle(
            0, PADDLE_Y, 0, PADDLE_Y + PADDLE_H, fill="#ecf0f1", outline="")
        self.ball = self.canvas.create_oval(0, 0, 0, 0, fill="#ffffff", outline="")
        self.hud = self.canvas.create_text(
            10, 10, anchor="nw", fill="#ecf0f1", font=("Consolas", 14))
        self.message = self.canvas.create_text(
            WIDTH / 2, HEIGHT / 2 + 40, fill="#ecf0f1",
            font=("Malgun Gothic", 16, "bold"), justify="center")

        self.speed = BALL_START_SPEED + (self.level - 1) * 0.5
        self.reset_ball()
        self.update_hud()

    def reset_ball(self):
        """공을 패들 위에 올려놓고 발사 대기 상태로."""
        self.bx = self.paddle_x
        self.by = PADDLE_Y - BALL_R - 1
        self.vx = self.vy = 0.0
        self.state = "ready"
        self.show_message("스페이스 / 클릭으로 발사")

    def launch(self):
        angle = math.radians(random.uniform(-30, 30))
        self.vx = self.speed * math.sin(angle)
        self.vy = -self.speed * math.cos(angle)
        self.state = "playing"
        self.show_message("")

    def show_message(self, text):
        self.canvas.itemconfigure(self.message, text=text)

    def update_hud(self):
        self.canvas.itemconfigure(
            self.hud,
            text=f"점수 {self.score}    목숨 {'♥' * self.lives}    레벨 {self.level}")

    # ---------- 입력 ----------
    def on_key_press(self, event):
        key = event.keysym
        self.keys.add(key)
        if key == "space":
            self.primary_action()
        elif key in ("p", "P"):
            if self.state == "playing":
                self.state = "paused"
                self.show_message("일시정지 (P)")
            elif self.state == "paused":
                self.state = "playing"
                self.show_message("")

    def on_key_release(self, event):
        self.keys.discard(event.keysym)

    def on_mouse_move(self, event):
        self.paddle_x = event.x

    def on_click(self, event):
        self.paddle_x = event.x
        self.primary_action()

    def primary_action(self):
        if self.state == "ready":
            self.launch()
        elif self.state == "gameover":
            self.new_game()
        elif self.state == "win":
            self.level += 1
            self.build_level()

    # ---------- 메인 루프 ----------
    def tick(self):
        if self.state in ("ready", "playing"):
            self.move_paddle()
        if self.state == "playing":
            self.move_ball()
        elif self.state == "ready":
            self.bx = self.paddle_x
        self.draw()
        self.root.after(FPS_DELAY, self.tick)

    def move_paddle(self):
        if "Left" in self.keys:
            self.paddle_x -= PADDLE_SPEED
        if "Right" in self.keys:
            self.paddle_x += PADDLE_SPEED
        half = PADDLE_W / 2
        self.paddle_x = max(half, min(WIDTH - half, self.paddle_x))

    def move_ball(self):
        # 빠른 공이 벽돌을 뚫지 않도록 여러 번 나눠서 이동
        steps = max(1, int(self.speed // 4) + 1)
        for _ in range(steps):
            self.bx += self.vx / steps
            self.by += self.vy / steps
            self.collide_walls()
            self.collide_paddle()
            self.collide_bricks()
            if self.state != "playing":
                return
            if self.by - BALL_R > HEIGHT:
                self.lose_life()
                return

    def collide_walls(self):
        if self.bx - BALL_R < 0:
            self.bx = BALL_R
            self.vx = abs(self.vx)
        elif self.bx + BALL_R > WIDTH:
            self.bx = WIDTH - BALL_R
            self.vx = -abs(self.vx)
        if self.by - BALL_R < 0:
            self.by = BALL_R
            self.vy = abs(self.vy)

    def collide_paddle(self):
        half = PADDLE_W / 2
        left = self.paddle_x - half
        right = self.paddle_x + half
        if (self.vy > 0
                and PADDLE_Y <= self.by + BALL_R <= PADDLE_Y + PADDLE_H + self.speed
                and left - BALL_R <= self.bx <= right + BALL_R):
            # 맞은 위치에 따라 반사각 결정 (가장자리일수록 비스듬하게)
            offset = (self.bx - self.paddle_x) / (half + BALL_R)
            offset = max(-1.0, min(1.0, offset))
            angle = offset * math.radians(60)
            self.vx = self.speed * math.sin(angle)
            self.vy = -self.speed * math.cos(angle)
            self.by = PADDLE_Y - BALL_R

    def collide_bricks(self):
        for item, (row, x1, y1, x2, y2) in list(self.bricks.items()):
            # 원-사각형 충돌: 사각형에서 공 중심에 가장 가까운 점
            nx = max(x1, min(self.bx, x2))
            ny = max(y1, min(self.by, y2))
            dx, dy = self.bx - nx, self.by - ny
            if dx * dx + dy * dy > BALL_R * BALL_R:
                continue

            # 겹침이 적은 축 방향으로 반사
            overlap_x = min(self.bx + BALL_R - x1, x2 - (self.bx - BALL_R))
            overlap_y = min(self.by + BALL_R - y1, y2 - (self.by - BALL_R))
            if overlap_x < overlap_y:
                self.vx = -self.vx
            else:
                self.vy = -self.vy

            self.canvas.delete(item)
            del self.bricks[item]
            self.score += ROW_POINTS[row]
            self.speed = min(BALL_MAX_SPEED, self.speed + 0.05)
            self.rescale_velocity()
            self.update_hud()

            if not self.bricks:
                self.state = "win"
                self.show_message(f"레벨 {self.level} 클리어!\n스페이스 / 클릭으로 다음 레벨")
            return  # 한 프레임에 벽돌 하나만 처리

    def rescale_velocity(self):
        """속도가 올라갔을 때 방향은 유지하고 크기만 맞춘다."""
        mag = math.hypot(self.vx, self.vy)
        if mag:
            self.vx *= self.speed / mag
            self.vy *= self.speed / mag

    def lose_life(self):
        self.lives -= 1
        self.update_hud()
        if self.lives <= 0:
            self.state = "gameover"
            self.show_message(f"GAME OVER\n최종 점수 {self.score}\n스페이스 / 클릭으로 다시 시작")
        else:
            self.reset_ball()

    # ---------- 그리기 ----------
    def draw(self):
        half = PADDLE_W / 2
        self.canvas.coords(self.paddle, self.paddle_x - half, PADDLE_Y,
                           self.paddle_x + half, PADDLE_Y + PADDLE_H)
        self.canvas.coords(self.ball, self.bx - BALL_R, self.by - BALL_R,
                           self.bx + BALL_R, self.by + BALL_R)


def main():
    root = tk.Tk()
    Breakout(root)
    root.mainloop()


if __name__ == "__main__":
    main()
