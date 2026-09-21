"""SNAKE DUEL - 사람 뱀 vs AI 뱀, 사과 먹기 대결 (tkinter 전용, 별도 설치 불필요)

규칙
  - 맵에는 항상 사과가 여러 개 있고, 먼저 TARGET개를 먹는 쪽이 승리
  - 벽 / 자기 몸 / 상대 몸에 부딪히면 폭발 후 잠시 뒤 다시 출발 (점수는 유지)

조작
  방향키 / WASD : 이동          Space (누르고 있기) : 대시 (게이지 소모)
  1 / 2 / 3 : AI 난이도(쉬움/보통/어려움)
  P : 일시정지   R / Enter : 재시작   Esc : 종료
"""
import math
import random
import time
import tkinter as tk
from collections import deque

CELL = 26
COLS, ROWS = 26, 20
W, H = COLS * CELL, ROWS * CELL
HUD_H = 46

BG = "#0d1117"
GRID = "#131a24"
FOOD_COLOR = "#ff4d6d"

TARGET = 10            # 승리에 필요한 사과 수
FOOD_COUNT = 3         # 맵 위 사과 개수
RESPAWN_TIME = 2.0

BASE_STEP = 0.15       # 칸 이동 시간(초)
MIN_STEP = 0.07
BOOST_FACTOR = 0.5     # 대시 시 이동 시간 배율

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]

# 난이도: (이름, AI 이동시간 배율(작을수록 빠름), 실수 확률)
DIFFICULTY = {1: ("쉬움", 1.2, 0.12), 2: ("보통", 1.0, 0.0), 3: ("어려움", 0.86, 0.0)}


def mix(c1, c2, t):
    """두 #rrggbb 색을 t(0~1) 비율로 섞는다."""
    t = max(0.0, min(1.0, t))
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def ease_out_back(t):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def inside(c):
    return 0 <= c[0] < COLS and 0 <= c[1] < ROWS


class Snake:
    def __init__(self, name, is_ai, palette, spawn, direction):
        self.name = name
        self.is_ai = is_ai
        self.tail_c, self.body_c, self.head_c = palette
        self.spawn = spawn
        self.spawn_dir = direction
        self.score = 0
        self.energy = 1.0          # 대시 게이지 (사람 전용)
        self.locked = False
        self.boosting = False
        self.respawn = 0.0
        self.place()

    def place(self):
        x, y = self.spawn
        dx, dy = self.spawn_dir
        self.body = [(x - dx * i, y - dy * i) for i in range(3)]
        self.prev = list(self.body)
        self.dir = self.spawn_dir
        self.queue = deque(maxlen=2)
        self.acc = 0.0
        self.bulges = []           # 몸통을 따라 이동하는 굵기 파동
        self.alive = True
        self.waiting = not self.is_ai   # 사람은 첫 입력을 기다렸다가 출발


class Game:
    def __init__(self, root):
        self.root = root
        self.canvas = tk.Canvas(root, width=W, height=H + HUD_H, bg=BG, highlightthickness=0)
        self.canvas.pack()
        self.time = 0.0
        self.paused = False
        self.difficulty = 2
        self.wins = [0, 0]           # [사람, AI]
        self.boost_held = False
        self.space_down = False
        self.release_job = None
        self.draw_background()
        self.bind_keys()
        self.reset()
        self.last = time.perf_counter()
        self.frame()

    # ------------------------------------------------------------------ 설정
    def bind_keys(self):
        r = self.root
        keys = {
            "Up": (0, -1), "w": (0, -1), "W": (0, -1),
            "Down": (0, 1), "s": (0, 1), "S": (0, 1),
            "Left": (-1, 0), "a": (-1, 0), "A": (-1, 0),
            "Right": (1, 0), "d": (1, 0), "D": (1, 0),
        }
        for k, d in keys.items():
            r.bind("<%s>" % k if len(k) > 1 else "<Key-%s>" % k, lambda e, d=d: self.turn(d))
        r.bind("<KeyPress-space>", self.on_space_press)
        r.bind("<KeyRelease-space>", self.on_space_release)
        for k in "pP":
            r.bind("<Key-%s>" % k, lambda e: self.toggle_pause())
        for k in "rR":
            r.bind("<Key-%s>" % k, lambda e: self.reset())
        r.bind("<Return>", lambda e: self.reset() if self.state == "over" else None)
        for n in DIFFICULTY:
            r.bind("<Key-%d>" % n, lambda e, n=n: setattr(self, "difficulty", n))
        r.bind("<Escape>", lambda e: r.destroy())

    def draw_background(self):
        c = self.canvas
        for y in range(ROWS):
            for x in range(COLS):
                if (x + y) % 2 == 0:
                    c.create_rectangle(x * CELL, HUD_H + y * CELL, (x + 1) * CELL, HUD_H + (y + 1) * CELL,
                                       fill=GRID, outline="")
        c.create_rectangle(1, HUD_H + 1, W - 1, HUD_H + H - 1, outline="#243042", width=2)

    def reset(self):
        self.player = Snake("YOU", False, ("#0b6e4f", "#2ee59d", "#b8ffe0"), (5, ROWS - 6), (1, 0))
        self.ai = Snake("AI", True, ("#3b2a8f", "#8b7bff", "#e4e0ff"), (COLS - 6, 5), (-1, 0))
        self.snakes = [self.ai, self.player]      # 그리는 순서: 사람이 위에
        self.state = "ready"                      # ready -> play -> over
        self.winner = None
        self.foods = []
        self.particles = []
        self.popups = []
        self.shake = 0.0
        self.flash = 0.0
        self.top_up_foods()

    def other(self, s):
        return self.ai if s is self.player else self.player

    # ------------------------------------------------------------------ 입력
    def turn(self, d):
        p = self.player
        if self.state == "over" or self.paused or not p.alive:
            return
        last = p.queue[-1] if p.queue else p.dir
        if d == last or (d[0] == -last[0] and d[1] == -last[1]):
            return
        p.queue.append(d)
        p.waiting = False
        if self.state == "ready":
            self.state = "play"

    def on_space_press(self, e):
        if self.release_job:                       # 키 반복 입력이면 해제 예약을 취소
            self.root.after_cancel(self.release_job)
            self.release_job = None
        self.boost_held = True
        if not self.space_down:
            self.space_down = True
            if self.state == "over":
                self.reset()

    def on_space_release(self, e):
        def release():
            self.release_job = None
            self.boost_held = False
            self.space_down = False
        self.release_job = self.root.after(40, release)

    def toggle_pause(self):
        if self.state == "play":
            self.paused = not self.paused

    # ------------------------------------------------------------------ 사과
    def food_at(self, cell):
        for f in self.foods:
            if f[0] == cell:
                return f
        return None

    def top_up_foods(self):
        while len(self.foods) < FOOD_COUNT:
            occupied = {f[0] for f in self.foods}
            for s in self.snakes:
                if s.alive:
                    occupied |= set(s.body)
            free = [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in occupied]
            if not free:
                break
            self.foods.append([random.choice(free), self.time])

    def cell_center(self, cell):
        return cell[0] * CELL + CELL / 2, HUD_H + cell[1] * CELL + CELL / 2

    # ------------------------------------------------------------------ 로직
    def step_time(self, s):
        t = max(MIN_STEP, BASE_STEP - 0.0035 * s.score)
        if s.is_ai:
            t *= DIFFICULTY[self.difficulty][1]
        elif s.boosting:
            t *= BOOST_FACTOR
        return t

    def step(self, s):
        if s.is_ai:
            s.dir = self.ai_choose(s)
        elif s.queue:
            s.dir = s.queue.popleft()
        head = s.body[0]
        new = (head[0] + s.dir[0], head[1] + s.dir[1])
        food = self.food_at(new)
        blocked = set(s.body if food else s.body[:-1])
        other = self.other(s)
        if other.alive:
            blocked |= set(other.body)
        if not inside(new) or new in blocked:
            self.die(s)
            return

        s.prev = list(s.body)
        s.body = [new] + (s.body if food else s.body[:-1])
        s.bulges = [b + 1 for b in s.bulges if b + 1 <= len(s.body) + 1]

        if food:
            self.foods.remove(food)
            s.score += 1
            fx, fy = self.cell_center(new)
            self.burst(fx, fy, 16, FOOD_COLOR, speed=180)
            self.popups.append([fx, fy - 8, "+1", 0.8, s.body_c])
            s.bulges.append(0.0)
            self.shake = max(self.shake, 2.5 if not s.is_ai else 1.2)
            self.top_up_foods()
            if s.score >= TARGET:
                self.finish(s)
                return
        if s.boosting:
            tx, ty = self.cell_center(s.prev[-1])
            self.burst(tx, ty, 2, mix(s.body_c, "#ffffff", 0.4), speed=50, life=0.35)

    def die(self, s):
        s.alive = False
        s.boosting = False
        s.respawn = RESPAWN_TIME
        hx, hy = self.cell_center(s.body[0])
        self.burst(hx, hy, 40, "#ff6b6b", speed=260, life=0.9)
        for seg in s.body[1:]:
            sx, sy = self.cell_center(seg)
            self.burst(sx, sy, 2, s.body_c, speed=120, life=0.8)
        self.popups.append([hx, hy - 12, "CRASH!", 1.0, "#ff6b6b"])
        if s is self.player:
            self.shake = 14.0
            self.flash = 0.35
        else:
            self.shake = max(self.shake, 6.0)

    def try_respawn(self, s):
        old = s.body
        s.place()
        other = self.other(s)
        x, y = s.spawn
        dx, dy = s.spawn_dir
        zone = set(s.body) | {(x + dx * i, y + dy * i) for i in range(1, 4)}
        if other.alive and zone & set(other.body):    # 상대가 자리를 막고 있으면 잠시 뒤 재시도
            s.body = old
            s.alive = False
            s.respawn = 0.15
            return
        self.foods = [f for f in self.foods if f[0] not in s.body]
        self.top_up_foods()
        px, py = self.cell_center(s.body[0])
        self.burst(px, py, 18, s.body_c, speed=140, life=0.6)
        s.boosting = False

    def finish(self, s):
        self.state = "over"
        self.winner = s
        self.wins[0 if s is self.player else 1] += 1
        for _ in range(4):
            self.firework(s)

    def firework(self, s):
        x = random.uniform(80, W - 80)
        y = HUD_H + random.uniform(60, H - 120)
        for color in (s.body_c, s.head_c, "#ffe066"):
            self.burst(x, y, 12, color, speed=220, life=1.0)

    def burst(self, x, y, n, color, speed=150, life=0.6):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(0.3, 1.0) * speed
            self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v,
                                   life * random.uniform(0.6, 1.0), life, color, random.uniform(2, 4.5)])

    # ------------------------------------------------------------------ AI
    def bfs(self, head, blocked):
        """head에서 갈 수 있는 모든 칸까지의 거리와, 그 칸으로 가는 첫 방향."""
        dist = {head: 0}
        first = {}
        q = deque()
        for d in DIRS:
            n = (head[0] + d[0], head[1] + d[1])
            if inside(n) and n not in blocked and n not in dist:
                dist[n] = 1
                first[n] = d
                q.append(n)
        while q:
            c = q.popleft()
            for d in DIRS:
                n = (c[0] + d[0], c[1] + d[1])
                if inside(n) and n not in blocked and n not in dist:
                    dist[n] = dist[c] + 1
                    first[n] = first[c]
                    q.append(n)
        return dist, first

    def room(self, s, n, other, cap):
        """n으로 이동한 뒤 머리가 갇히지 않고 움직일 수 있는 칸 수 (cap까지만 셈)."""
        eating = self.food_at(n) is not None
        new_body = [n] + (s.body if eating else s.body[:-1])
        blk = set(new_body[1:-1])
        if other.alive:
            blk |= set(other.body)
        seen = {n}
        q = deque([n])
        while q and len(seen) < cap:
            c = q.popleft()
            for d in DIRS:
                m = (c[0] + d[0], c[1] + d[1])
                if inside(m) and m not in blk and m not in seen:
                    seen.add(m)
                    q.append(m)
        return len(seen)

    def ai_choose(self, s):
        other = self.other(s)
        head = s.body[0]
        blocked = set(s.body[:-1])
        danger = set()
        if other.alive:
            blocked |= set(other.body)
            oh = other.body[0]
            danger = {(oh[0] + dx, oh[1] + dy) for dx, dy in DIRS}   # 상대 머리와 정면충돌 방지

        moves = [(d, (head[0] + d[0], head[1] + d[1])) for d in DIRS]
        moves = [(d, n) for d, n in moves if inside(n) and n not in blocked]
        if not moves:
            return s.dir

        pool = [m for m in moves if m[1] not in danger] or moves
        need = min(len(s.body) + 1, 40)
        sizes = {n: self.room(s, n, other, need) for _, n in pool}
        good = [(d, n) for d, n in pool if sizes[n] >= need]

        # 난이도 '쉬움'은 가끔 아무 안전한 방향으로 헛발질
        if good and random.random() < DIFFICULTY[self.difficulty][2]:
            return random.choice(good)[0]

        food_cells = [f[0] for f in self.foods]
        dist, first = self.bfs(head, blocked)
        cands = sorted((dist[f], f) for f in food_cells if f in dist)
        if other.alive:      # 상대보다 먼저 도착할 수 있는 사과를 우선
            ph = other.body[0]
            win = [c for c in cands if c[0] <= abs(ph[0] - c[1][0]) + abs(ph[1] - c[1][1])]
            cands = win + [c for c in cands if c not in win]
        good_dirs = {d for d, _ in good}
        for _, f in cands:
            if first[f] in good_dirs:
                return first[f]

        if good:             # 사과로 가는 길이 위험하면 가장 가까워지는 안전한 방향
            def gap(m):
                return min((abs(m[1][0] - f[0]) + abs(m[1][1] - f[1]) for f in food_cells), default=0)
            return min(good, key=gap)[0]
        return max(pool, key=lambda m: sizes[m[1]])[0]      # 다 위험하면 가장 넓은 쪽

    # ------------------------------------------------------------------ 루프
    def frame(self):
        now = time.perf_counter()
        dt = min(now - self.last, 0.05)
        self.last = now
        if self.paused:
            dt = 0.0
        self.time += dt

        if self.state == "play":
            self.update_boost(dt)
            for s in self.snakes:
                if not s.alive:
                    s.respawn -= dt
                    if s.respawn <= 0:
                        self.try_respawn(s)
                    continue
                if s.waiting:
                    continue
                s.acc += dt
                while s.alive and self.state == "play" and s.acc >= self.step_time(s):
                    s.acc -= self.step_time(s)
                    self.step(s)

        self.update_effects(dt)
        self.draw()
        self.root.after(16, self.frame)

    def update_boost(self, dt):
        p = self.player
        if self.boost_held and p.alive and not p.waiting and not p.locked and p.energy > 0:
            p.boosting = True
            p.energy = max(0.0, p.energy - 0.8 * dt)
            if p.energy <= 0:
                p.locked = True
        else:
            p.boosting = False
            p.energy = min(1.0, p.energy + 0.3 * dt)
            if p.locked and p.energy >= 0.3:
                p.locked = False

    def update_effects(self, dt):
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 260 * dt            # 중력
            p[2] *= 1 - 1.5 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for pop in self.popups:
            pop[1] -= 40 * dt
            pop[3] -= dt
        self.popups = [p for p in self.popups if p[3] > 0]
        self.shake = max(0.0, self.shake - 30 * dt)
        self.flash = max(0.0, self.flash - dt)
        if self.state == "over" and random.random() < dt * 3:
            self.firework(self.winner)

    # ------------------------------------------------------------------ 렌더
    def draw(self):
        c = self.canvas
        c.delete("dyn")
        ox = random.uniform(-self.shake, self.shake) if self.shake else 0.0
        oy = random.uniform(-self.shake, self.shake) if self.shake else 0.0

        for f, born in self.foods:
            self.draw_food(f, born, ox, oy)
        for s in self.snakes:
            if s.alive:
                self.draw_snake(s, ox, oy)
            elif self.state == "play":
                x, y = self.cell_center(s.spawn)
                c.create_text(x, y, text="%.1f" % max(0.0, s.respawn), fill=s.body_c,
                              font=("Consolas", 14, "bold"), tags="dyn")
        self.draw_particles(ox, oy)
        self.draw_hud()

        if self.flash > 0:
            c.create_rectangle(0, HUD_H, W, HUD_H + H, fill="#ff2a2a",
                               stipple="gray25" if self.flash > 0.15 else "gray12", outline="", tags="dyn")
        name = DIFFICULTY[self.difficulty][0]
        if self.state == "ready":
            self.banner("SNAKE DUEL", "#2ee59d",
                        ["사과 %d개를 먼저 먹으면 승리!   방향키 / WASD 로 시작" % TARGET,
                         "Space: 대시   ·   1/2/3: AI 난이도 (현재 %s)   ·   P: 일시정지" % name])
        elif self.state == "over":
            win = self.winner is self.player
            self.banner("YOU WIN!" if win else "AI WINS", self.winner.body_c,
                        ["전적  YOU %d : %d AI" % tuple(self.wins),
                         "R / Enter / Space: 다시 시작   ·   1/2/3: 난이도 (현재 %s)" % name])
        elif self.paused:
            self.banner("PAUSED", "#2ee59d", ["P: 계속하기"])

    def oval(self, x, y, r, **kw):
        self.canvas.create_oval(x - r, y - r, x + r, y + r, tags="dyn", **kw)

    def draw_food(self, cell, born_time, ox, oy):
        fx, fy = self.cell_center(cell)
        fx += ox
        fy += oy
        born = min(1.0, (self.time - born_time) / 0.35)
        pulse = 1 + 0.1 * math.sin(self.time * 7 + cell[0])
        r = CELL * 0.33 * pulse * max(0.0, ease_out_back(born))
        glow = 0.5 + 0.5 * math.sin(self.time * 4 + cell[1])
        self.oval(fx, fy, r + 7 + 3 * glow, fill="", outline=mix(BG, FOOD_COLOR, 0.25 + 0.2 * glow), width=2)
        self.oval(fx, fy, r, fill=FOOD_COLOR, outline=mix(FOOD_COLOR, "#ffffff", 0.35), width=2)
        self.oval(fx - r * 0.35, fy - r * 0.35, r * 0.22, fill="#ffd6de", outline="")
        self.canvas.create_line(fx, fy - r, fx + 4, fy - r - 6 * born, fill="#3ddc84", width=3,
                                capstyle=tk.ROUND, tags="dyn")

    def snake_points(self, s):
        """보간된 몸통 좌표(픽셀) 리스트, 머리부터."""
        alpha = 0.0 if s.waiting else min(1.0, s.acc / self.step_time(s))
        pts = []
        for i, cur in enumerate(s.body):
            start = s.prev[i] if i < len(s.prev) else s.prev[-1]
            x = start[0] + (cur[0] - start[0]) * alpha
            y = start[1] + (cur[1] - start[1]) * alpha
            pts.append((x * CELL + CELL / 2, HUD_H + y * CELL + CELL / 2))
        return pts, alpha

    def draw_snake(self, s, ox, oy):
        pts, alpha = self.snake_points(s)
        n = len(pts)
        amp_scale = 3.6 if s.boosting else 2.4
        phase = 0.0 if not s.is_ai else 1.7

        # 몸통이 물결치도록 진행 방향의 수직으로 살짝 흔든다
        wavy = []
        for i, (x, y) in enumerate(pts):
            if i > 0:
                a = pts[i - 1]
                b = pts[i + 1] if i + 1 < n else pts[i]
                dx, dy = a[0] - b[0], a[1] - b[1]
                ln = math.hypot(dx, dy) or 1.0
                w = math.sin(self.time * 9 - i * 0.7 + phase) * amp_scale * min(1.0, i / 3) * (1 - 0.6 * i / n)
                x += -dy / ln * w
                y += dx / ln * w
            wavy.append((x + ox, y + oy))

        # 굵기: 꼬리 쪽이 가늘고, 먹이 파동이 지나가면 부풀어 오른다
        bulge_pos = [b + alpha for b in s.bulges]
        radii = []
        for i in range(n):
            r = CELL * 0.46 * (1 - 0.42 * i / max(1, n - 1))
            for bp in bulge_pos:
                r += CELL * 0.16 * max(0.0, 1 - abs(i - bp) / 1.6)
            radii.append(r)
        colors = [mix(s.body_c, s.tail_c, i / max(1, n - 1)) for i in range(n)]

        for i in range(n - 1, -1, -1):                       # 그림자
            x, y = wavy[i]
            self.oval(x + 2, y + 4, radii[i], fill="#070a0f", outline="")

        for i in range(n - 1, 0, -1):
            (x1, y1), (x2, y2) = wavy[i], wavy[i - 1]
            self.canvas.create_line(x1, y1, x2, y2, width=radii[i] * 2, fill=colors[i],
                                    capstyle=tk.ROUND, tags="dyn")
            self.oval(x1, y1, radii[i], fill=colors[i], outline="")
            if i % 2 == 0:                                   # 등 무늬
                self.oval(x1, y1, radii[i] * 0.45, fill=mix(colors[i], "#ffffff", 0.18), outline="")

        self.draw_head(s, wavy[0], radii[0])

    def draw_head(self, s, pos, r):
        x, y = pos
        dx, dy = s.dir
        px, py = -dy, dx
        self.oval(x, y, r * 1.08, fill=s.head_c, outline=mix(s.head_c, "#000000", 0.25), width=2)

        if math.sin(self.time * 6 + (2 if s.is_ai else 0)) > 0.55:        # 혀 낼름
            ex, ey = x + dx * r * 1.9, y + dy * r * 1.9
            self.canvas.create_line(x + dx * r, y + dy * r, ex, ey, fill="#ff3b5c", width=2, tags="dyn")
            for k in (-1, 1):
                self.canvas.create_line(ex, ey, ex + dx * 4 + px * 4 * k, ey + dy * 4 + py * 4 * k,
                                        fill="#ff3b5c", width=2, tags="dyn")

        for k in (-1, 1):                                                  # 눈
            ex = x + dx * r * 0.35 + px * r * 0.52 * k
            ey = y + dy * r * 0.35 + py * r * 0.52 * k
            er = r * (0.36 if s.boosting else 0.3)
            self.oval(ex, ey, er, fill="#ffffff", outline="")
            self.oval(ex + dx * er * 0.35, ey + dy * er * 0.35, er * 0.55, fill="#0b0f14", outline="")

        label = s.name
        if s.waiting and self.state == "play":
            label = "방향키로 출발!"
        self.canvas.create_text(x, y - r - 12, text=label, fill=s.body_c,
                                font=("Segoe UI", 9, "bold"), tags="dyn")

    def draw_particles(self, ox, oy):
        for x, y, _, _, life, max_life, color, size in self.particles:
            k = life / max_life
            self.oval(x + ox, y + oy, size * (0.4 + 0.6 * k), fill=mix(BG, color, 0.25 + 0.75 * k), outline="")
        for x, y, text, life, color in self.popups:
            k = min(1.0, life / 0.4)
            self.canvas.create_text(x + ox, y + oy, text=text, fill=mix(BG, color, k),
                                    font=("Segoe UI", 16, "bold"), tags="dyn")

    def draw_hud(self):
        c = self.canvas
        c.create_rectangle(0, 0, W, HUD_H, fill="#0a0e14", outline="", tags="dyn")
        bar_w = 170
        for s, x0, anchor, label in ((self.player, 14, "w", "YOU"),
                                     (self.ai, W - 14, "e", "AI (%s)" % DIFFICULTY[self.difficulty][0])):
            c.create_text(x0, 14, anchor=anchor, text="%s   %d / %d" % (label, s.score, TARGET),
                          fill=s.body_c, font=("Segoe UI", 12, "bold"), tags="dyn")
            bx0 = x0 if anchor == "w" else x0 - bar_w
            c.create_line(bx0, 33, bx0 + bar_w, 33, fill="#1f2a3a", width=7, capstyle=tk.ROUND, tags="dyn")
            if s.score:
                c.create_line(bx0, 33, bx0 + bar_w * min(1.0, s.score / TARGET), 33, fill=s.body_c,
                              width=7, capstyle=tk.ROUND, tags="dyn")

        # 대시 게이지
        p = self.player
        c.create_text(W / 2, 12, text="DASH", fill="#8b98a9", font=("Consolas", 9, "bold"), tags="dyn")
        c.create_line(W / 2 - 50, 31, W / 2 + 50, 31, fill="#1f2a3a", width=8, capstyle=tk.ROUND, tags="dyn")
        if p.energy > 0.02:
            color = "#6b3b3b" if p.locked else mix("#2ee59d", "#ffd166", 1 - p.energy)
            c.create_line(W / 2 - 50, 31, W / 2 - 50 + 100 * p.energy, 31, fill=color, width=8,
                          capstyle=tk.ROUND, tags="dyn")

    def banner(self, title, color, lines):
        c = self.canvas
        cx, cy = W / 2, HUD_H + H / 2
        bob = math.sin(self.time * 3) * 4
        c.create_rectangle(cx - 280, cy - 75 + bob, cx + 280, cy + 75 + bob, fill="#0d1117",
                           outline=color, width=2, tags="dyn")
        c.create_text(cx, cy - 34 + bob, text=title, fill=color, font=("Consolas", 32, "bold"), tags="dyn")
        for i, line in enumerate(lines):
            c.create_text(cx, cy + 12 + i * 24 + bob, text=line, fill="#c9d4e0",
                          font=("Segoe UI", 10), tags="dyn")


def main():
    root = tk.Tk()
    root.title("Snake Duel")
    root.resizable(False, False)
    Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()
