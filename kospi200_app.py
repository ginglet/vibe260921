"""코스피200 편입종목 상위 - PyQt6 GUI 앱 (에디토리얼 / 신문 시세면 스타일)

크롤링 로직은 kospi200_crawler.py 를 그대로 재사용합니다. (같은 폴더에 두세요)

실행
  pip install PyQt6 requests openpyxl
  python kospi200_app.py

사용법
  1) [불러오기]를 누르면 코스피200 편입종목(약 200개)을 순위대로 가져와 표에 채웁니다.
  2) 열 제목을 누르면 그 기준으로 정렬, 검색창에 종목명/코드를 입력하면 바로 걸러집니다.
  3) 종목을 더블클릭하면 브라우저로 종목 페이지가 열립니다.
  4) [엑셀 저장] / [CSV 저장] / [JSON 저장]으로 내보냅니다. (걸러 놓은 것과 상관없이 수집한 전체가 저장됩니다)

주의: 이 데이터는 네이버 증권(Npay 증권)의 비공식 JSON 주소에서 가져옵니다. robots.txt 와 약관상 자동 수집이
      제한될 수 있으니 개인 학습용으로 소량만 쓰세요. 데이터는 지연·오류가 있을 수 있어 투자 판단의 근거로 쓰면 안 됩니다.
      자세한 내용은 kospi200_crawler.py 상단을 참고하세요.
"""
import sys
from datetime import datetime

from PyQt6.QtCore import QObject, QRect, QSize, Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QPen
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton, QSizePolicy, QSpinBox, QStackedWidget,
    QStyle, QStyledItemDelegate, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import kospi200_crawler as kc

# ---------------------------------------------------------------- 디자인 토큰 (종이 + 잉크, 상승 빨강 / 하락 파랑)
PAPER = "#F3EEE3"
PAPER_LIGHT = "#FAF7F0"
PAPER_DARK = "#E9E2D2"
INK = "#16130F"
MUTED = "#6B645A"
RULE_SOFT = "#CFC7B7"
ACCENT = "#7A5C1E"          # 포인트(황동색). 빨강/파랑은 시세 방향 전용으로 남겨 둔다
UP = "#C62828"
DOWN = "#1565C0"

SERIF = "Georgia"
SANS = "Malgun Gothic"
WEEKDAYS = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]

COLUMNS = ["순위", "종목명", "종목코드", "현재가(원)", "전일비(원)", "등락률", "거래량(주)", "거래대금(백만)", "시가총액(억)"]
CENTER_COLS = {0, 2}
RIGHT_COLS = {3, 4, 5, 6, 7, 8}


def pick_font(candidates, default):
    have = set(QFontDatabase.families())
    return next((c for c in candidates if c in have), default)


def init_fonts():
    global SERIF, SANS
    SERIF = pick_font(["Noto Serif KR", "Noto Serif CJK KR", "Nanum Myeongjo", "NanumMyeongjo",
                       "Batang", "바탕", "Georgia", "Times New Roman"], "serif")
    SANS = pick_font(["Pretendard", "Noto Sans KR", "Malgun Gothic", "맑은 고딕"], "sans-serif")


def make_font(size, *, bold=False, italic=False, spacing=0.0, serif=True):
    f = QFont(SERIF if serif else SANS)
    f.setPixelSize(size)
    f.setBold(bold)
    f.setItalic(italic)
    if spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return f


def label(text, size, *, bold=False, italic=False, color=INK, spacing=0.0, serif=True, align=None):
    lab = QLabel(text)
    lab.setFont(make_font(size, bold=bold, italic=italic, spacing=spacing, serif=serif))
    lab.setStyleSheet(f"color:{color}; background:transparent;")
    if align is not None:
        lab.setAlignment(align)
    return lab


def set_label_color(lab, color):
    lab.setStyleSheet(f"color:{color}; background:transparent;")


def rule(height=1, color=INK):
    line = QFrame()
    line.setFixedHeight(height)
    line.setStyleSheet(f"background:{color}; border:none;")
    return line


def color_of(direction):
    return {"up": UP, "down": DOWN}.get(direction, MUTED)


def arrow_of(direction):
    return {"up": "▲", "down": "▼"}.get(direction, "–")


def fmt_num(value):
    return "-" if value is None else f"{value:,}"


# ---------------------------------------------------------------- 크롤링 작업 스레드
class CrawlWorker(QObject):
    summary = pyqtSignal(dict)           # 지수 요약 (실패하면 빈 dict)
    page = pyqtSignal(list)              # 새로 도착한 종목들
    progress = pyqtSignal(int)           # 지금까지 모은 종목 수
    status = pyqtSignal(str)
    done = pyqtSignal(int, str)          # 수집 종목 수, 종료 메시지

    def __init__(self, limit, delay):
        super().__init__()
        self.limit, self.delay = limit, delay
        self._stop = False
        self._count = 0

    def stop(self):
        self._stop = True

    def _on_progress(self, n):
        self._count = n
        self.progress.emit(n)

    def run(self):
        try:
            session = kc.new_session()
            self.status.emit("코스피200 지수 정보를 가져오는 중…")
            self.summary.emit(kc.fetch_index_summary(session, log=self.status.emit) or {})
            if self._stop:
                self.done.emit(0, "수집을 중지했습니다.")
                return
            self.status.emit("편입종목 상위 목록을 가져오는 중…")
            kc.fetch_constituents(
                limit=self.limit, delay=self.delay, session=session, log=self.status.emit,
                should_stop=lambda: self._stop, on_progress=self._on_progress, on_page=self.page.emit,
            )
            self.done.emit(self._count, "수집을 중지했습니다." if self._stop else "수집을 마쳤습니다.")
        except kc.CrawlError as e:
            self.done.emit(self._count, str(e))
        except Exception as e:      # 스레드 안의 예외가 앱을 죽이지 않도록
            self.done.emit(self._count, f"오류가 발생했습니다: {e}")


# ---------------------------------------------------------------- 표
class NumItem(QTableWidgetItem):
    """화면에는 '1,234' 로 보이지만 정렬은 숫자 값으로 한다."""

    def __init__(self, text, value):
        super().__init__(text)
        self.setData(Qt.ItemDataRole.UserRole, value)

    def __lt__(self, other):
        a, b = self.data(Qt.ItemDataRole.UserRole), other.data(Qt.ItemDataRole.UserRole)
        if a is None:
            return b is not None
        if b is None:
            return False
        return a < b


class QuoteTable(QTableWidget):
    def __init__(self):
        super().__init__(0, len(COLUMNS))
        self.hover_row = -1
        self.setMouseTracking(True)
        self.entered.connect(lambda idx: self._set_hover(idx.row()))

    def _set_hover(self, row):
        if row != self.hover_row:
            self.hover_row = row
            self.viewport().update()

    def leaveEvent(self, event):
        self._set_hover(-1)
        super().leaveEvent(event)


class QuoteDelegate(QStyledItemDelegate):
    """행 전체 호버/선택 배경, 얇은 구분선, 상승 빨강·하락 파랑 글자를 직접 그린다."""

    def __init__(self, table):
        super().__init__(table)
        self.table = table
        self.name_font = make_font(15, bold=True)
        self.num_font = make_font(14, serif=False)
        self.small_font = make_font(13, serif=False)

    def sizeHint(self, option, index):
        return QSize(80, 36)

    def paint(self, painter, option, index):
        r = option.rect
        col = index.column()
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = index.row() == self.table.hover_row

        painter.save()
        painter.fillRect(r, QColor(PAPER_DARK if selected else (PAPER_LIGHT if hovered else PAPER)))
        if selected and col == 0:
            painter.fillRect(QRect(r.left(), r.top(), 4, r.height()), QColor(INK))
        painter.setPen(QPen(QColor(RULE_SOFT), 1))
        painter.drawLine(r.left(), r.bottom(), r.right(), r.bottom())

        fg = index.data(Qt.ItemDataRole.ForegroundRole)
        painter.setPen(fg.color() if fg else QColor(INK))
        font = self.name_font if col == 1 else (self.small_font if col in (0, 2) else self.num_font)
        painter.setFont(font)
        text = painter.fontMetrics().elidedText(index.data(Qt.ItemDataRole.DisplayRole) or "",
                                                Qt.TextElideMode.ElideRight, r.width() - 24)
        if col in CENTER_COLS:
            align = Qt.AlignmentFlag.AlignCenter
        elif col in RIGHT_COLS:
            align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        else:
            align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        painter.drawText(r.adjusted(12, 0, -12, 0), int(align), text)
        painter.restore()


STYLE = """
QWidget#root, QMainWindow { background: @PAPER; }
QLineEdit, QSpinBox, QDoubleSpinBox {
    background: transparent; border: none; border-bottom: 1px solid @INK; padding: 5px 2px;
    color: @INK; selection-background-color: @ACCENT; selection-color: @PAPER;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-bottom: 2px solid @ACCENT; }
QPushButton { padding: 10px 24px; border: 1px solid @INK; font-weight: 600; }
QPushButton#primary { background: @INK; color: @PAPER; }
QPushButton#primary:hover { background: @ACCENT; border-color: @ACCENT; }
QPushButton#primary:disabled { background: #B9B2A3; border-color: #B9B2A3; color: @PAPER; }
QPushButton#ghost { background: transparent; color: @INK; }
QPushButton#ghost:hover { background: @INK; color: @PAPER; }
QPushButton#ghost:disabled { color: #A39B8C; border-color: @RULE_SOFT; }
QTableWidget { background: @PAPER; border: none; outline: 0; gridline-color: transparent; }
QHeaderView { background: @PAPER; }
QHeaderView::section {
    background: @PAPER; color: @INK; border: none; border-bottom: 2px solid @INK; padding: 8px 12px; font-weight: 700;
}
QHeaderView::section:hover { background: @PAPER_DARK; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: @RULE_SOFT; min-height: 36px; }
QScrollBar::handle:vertical:hover { background: @MUTED; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: @RULE_SOFT; min-width: 36px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QProgressBar { background: @RULE_SOFT; border: none; max-height: 3px; min-height: 3px; }
QProgressBar::chunk { background: @ACCENT; }
QToolTip { background: @INK; color: @PAPER; border: none; padding: 4px 8px; }
"""


def build_style():
    css = STYLE
    for name, value in (("PAPER_LIGHT", PAPER_LIGHT), ("PAPER_DARK", PAPER_DARK), ("PAPER", PAPER), ("INK", INK),
                        ("MUTED", MUTED), ("RULE_SOFT", RULE_SOFT), ("ACCENT", ACCENT)):
        css = css.replace("@" + name, value)
    return css


def placeholder_widget(message, sub=""):
    box = QWidget()
    v = QVBoxLayout(box)
    v.setAlignment(Qt.AlignmentFlag.AlignCenter)
    v.addWidget(label("§", 44, color=RULE_SOFT, align=Qt.AlignmentFlag.AlignCenter))
    box.msg = label(message, 20, italic=True, color=MUTED, align=Qt.AlignmentFlag.AlignCenter)
    box.sub = label(sub, 12, serif=False, color=MUTED, align=Qt.AlignmentFlag.AlignCenter)
    v.addWidget(box.msg)
    v.addWidget(box.sub)
    return box


# ---------------------------------------------------------------- 메인 창
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("코스피200 편입종목 상위")
        self.resize(1240, 860)
        self.setMinimumSize(1000, 640)

        self.rows = []
        self.summary = {}
        self.thread = None
        self.worker = None

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(36, 18, 36, 14)
        layout.setSpacing(0)

        layout.addWidget(self._build_masthead())
        layout.addSpacing(10)
        layout.addLayout(self._build_index_strip())
        layout.addSpacing(10)
        layout.addWidget(rule(1))
        layout.addSpacing(12)
        layout.addLayout(self._build_controls())
        layout.addSpacing(12)
        layout.addWidget(self._build_table_area(), 1)
        layout.addLayout(self._build_footer())

        self._refresh_summary()

    # ------------------------------------------------------------ UI 구성
    def _build_masthead(self):
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(rule(1))
        v.addSpacing(6)

        now = datetime.now()
        top = QGridLayout()
        top.setContentsMargins(0, 0, 0, 0)
        for col in range(3):
            top.setColumnStretch(col, 1)
        top.addWidget(label(f"{now.year}년 {now.month}월 {now.day}일 {WEEKDAYS[now.weekday()]}", 12, serif=False,
                            color=MUTED, spacing=0.5), 0, 0, Qt.AlignmentFlag.AlignLeft)
        top.addWidget(label("KOSPI 200  ·  CONSTITUENTS", 10, bold=True, serif=False, color=MUTED, spacing=3),
                      0, 1, Qt.AlignmentFlag.AlignCenter)
        self.date_lbl = label("", 12, italic=True, color=ACCENT)
        top.addWidget(self.date_lbl, 0, 2, Qt.AlignmentFlag.AlignRight)
        v.addLayout(top)

        v.addSpacing(2)
        v.addWidget(label("코스피200 편입종목", 50, bold=True, spacing=8, align=Qt.AlignmentFlag.AlignCenter))
        v.addWidget(label("지수를 이루는 대표 기업들을 순위대로 한눈에 봅니다", 13, italic=True, color=MUTED,
                          align=Qt.AlignmentFlag.AlignCenter))
        v.addSpacing(10)
        v.addWidget(rule(3))
        v.addSpacing(3)
        v.addWidget(rule(1))
        return box

    def _build_index_strip(self):
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(label("코스피200 지수", 12, bold=True, serif=False, color=MUTED, spacing=1.5),
                      0, Qt.AlignmentFlag.AlignBottom)
        self.level_lbl = label("0,000.00", 38, bold=True, color=RULE_SOFT)
        self.change_lbl = label("", 17, serif=False, bold=True, color=MUTED)
        row.addWidget(self.level_lbl, 0, Qt.AlignmentFlag.AlignBottom)
        row.addWidget(self.change_lbl, 0, Qt.AlignmentFlag.AlignBottom)
        row.addStretch()
        self.up_lbl = label("", 14, serif=False, bold=True, color=UP)
        self.flat_lbl = label("", 14, serif=False, bold=True, color=MUTED)
        self.down_lbl = label("", 14, serif=False, bold=True, color=DOWN)
        for lab in (self.up_lbl, self.flat_lbl, self.down_lbl):
            row.addWidget(lab, 0, Qt.AlignmentFlag.AlignBottom)
            row.addSpacing(8)
        return row

    def _field(self, caption, widget, width=None):
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        v.addWidget(label(caption, 10, bold=True, serif=False, color=MUTED, spacing=2))
        v.addWidget(widget)
        if width:
            box.setFixedWidth(width)
        return box

    def _build_controls(self):
        row = QHBoxLayout()
        row.setSpacing(24)

        self.filter_edit = QLineEdit()
        self.filter_edit.setFont(make_font(16, serif=True))
        self.filter_edit.setPlaceholderText("종목명 또는 종목코드로 걸러 보기  (예: 삼성, 005930)")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self.apply_filter)

        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(0, 250)
        self.limit_spin.setValue(0)
        self.limit_spin.setSpecialValueText("전체")
        self.limit_spin.setSuffix(" 종목")
        self.limit_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.limit_spin.setFont(make_font(15, serif=True))
        self.limit_spin.setToolTip("상위 몇 종목까지 가져올지 정합니다. 0(전체)이면 코스피200 전체(약 200개)입니다.")

        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.5, 10.0)
        self.delay_spin.setSingleStep(0.5)
        self.delay_spin.setDecimals(1)
        self.delay_spin.setValue(1.0)
        self.delay_spin.setSuffix(" 초")
        self.delay_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.delay_spin.setFont(make_font(15, serif=True))
        self.delay_spin.setToolTip("페이지 요청 사이 대기 시간입니다. 서버에 부담을 주지 않도록 0.5초 이상만 허용합니다.")

        self.start_btn = QPushButton("불러오기")
        self.start_btn.setObjectName("primary")
        self.stop_btn = QPushButton("중지")
        self.stop_btn.setObjectName("ghost")
        for b in (self.start_btn, self.stop_btn):
            b.setFont(make_font(13, bold=True, spacing=1.5, serif=False))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)

        row.addWidget(self._field("검색  FILTER", self.filter_edit), 1)
        row.addWidget(self._field("가져올 수  TOP N", self.limit_spin, 130))
        row.addWidget(self._field("대기  DELAY", self.delay_spin, 100))
        row.addWidget(self.start_btn, 0, Qt.AlignmentFlag.AlignBottom)
        row.addWidget(self.stop_btn, 0, Qt.AlignmentFlag.AlignBottom)
        return row

    def _build_table_area(self):
        self.stack = QStackedWidget()
        self.empty = placeholder_widget("편입종목이 여기에 실립니다", "‘불러오기’를 눌러 코스피200 종목을 가져오세요.")
        self.stack.addWidget(self.empty)

        self.table = QuoteTable()
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setItemDelegate(QuoteDelegate(self.table))
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        header = self.table.horizontalHeader()
        header.setFont(make_font(12, bold=True, spacing=1, serif=False))
        header.setSectionsClickable(True)
        header.setHighlightSections(False)
        header.setMinimumHeight(38)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col, width in {0: 64, 2: 96, 3: 120, 4: 120, 5: 90, 6: 130, 7: 140, 8: 140}.items():
            self.table.setColumnWidth(col, width)
        for col in range(len(COLUMNS)):
            head = self.table.horizontalHeaderItem(col)
            align = (Qt.AlignmentFlag.AlignCenter if col in CENTER_COLS else
                     Qt.AlignmentFlag.AlignRight if col in RIGHT_COLS else Qt.AlignmentFlag.AlignLeft)
            head.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
        self.table.itemDoubleClicked.connect(self._open_stock)
        self.stack.addWidget(self.table)
        return self.stack

    def _build_footer(self):
        v = QVBoxLayout()
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setValue(0)
        v.addWidget(self.progress)
        v.addSpacing(8)

        row = QHBoxLayout()
        self.status_lbl = label("준비되었습니다.  데이터는 지연·오류가 있을 수 있으니 투자 판단의 근거로 쓰지 마세요.", 13,
                                italic=True, color=MUTED)
        self.status_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        row.addWidget(self.status_lbl, 1)
        self.excel_btn = QPushButton("엑셀 저장")
        self.csv_btn = QPushButton("CSV 저장")
        self.json_btn = QPushButton("JSON 저장")
        self.save_buttons = (self.excel_btn, self.csv_btn, self.json_btn)
        for b, fn in ((self.excel_btn, self.save_excel), (self.csv_btn, self.save_csv), (self.json_btn, self.save_json)):
            b.setObjectName("ghost")
            b.setStyleSheet("padding: 6px 14px;")
            b.setFont(make_font(12, bold=True, spacing=1, serif=False))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setEnabled(False)
            b.setToolTip("걸러 놓은 것과 상관없이 수집한 전체 종목을 저장합니다.")
            b.clicked.connect(fn)
            row.addWidget(b)
        v.addLayout(row)
        return v

    # ------------------------------------------------------------ 동작
    def set_status(self, text):
        self.status_lbl.setText(text)

    def set_running(self, running):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.limit_spin.setEnabled(not running)
        self.delay_spin.setEnabled(not running)
        for b in self.save_buttons:
            b.setEnabled(bool(self.rows) and not running)

    def start(self):
        if self.thread is not None:
            return
        self.rows.clear()
        self.summary = {}
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        self.progress.setValue(0)
        self.progress.setMaximum(self.limit_spin.value() or 200)
        self._refresh_summary()
        self.empty.msg.setText("데이터를 가져오는 중입니다…")
        self.empty.sub.setText("잠시만 기다려 주세요.")
        self.stack.setCurrentWidget(self.empty)

        self.thread = QThread(self)
        self.worker = CrawlWorker(self.limit_spin.value() or None, self.delay_spin.value())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.summary.connect(self._on_summary)
        self.worker.page.connect(self.add_rows)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.status.connect(self.set_status)
        self.worker.done.connect(self._on_done)
        self.worker.done.connect(self.thread.quit)
        self.thread.finished.connect(self._on_thread_finished)
        self.set_running(True)
        self.set_status("수집을 시작합니다…")
        self.thread.start()

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.stop_btn.setEnabled(False)
            self.set_status("중지하는 중…")

    def _on_summary(self, summary):
        self.summary = summary
        self._refresh_summary()

    def add_rows(self, new_rows):
        self.stack.setCurrentWidget(self.table)
        for row in new_rows:
            self.rows.append(row)
            self._append_table_row(row)
        self.apply_filter()
        self._refresh_summary()

    def _append_table_row(self, r):
        color = QColor(color_of(r["direction"]))
        i = self.table.rowCount()
        self.table.insertRow(i)

        def num(col, text, value, colored=False):
            item = NumItem(text, value)
            if colored:
                item.setForeground(color)
            self.table.setItem(i, col, item)

        change = r["change"]
        change_text = f"{arrow_of(r['direction'])} {abs(change):,}" if change is not None else "-"
        rate = r["change_rate"]
        rate_text = f"{rate:+.2f}%" if rate is not None else "-"
        num(0, str(r["rank"]), r["rank"])
        name = QTableWidgetItem(r["name"])
        name.setData(Qt.ItemDataRole.UserRole + 1, r["url"])
        self.table.setItem(i, 1, name)
        self.table.setItem(i, 2, QTableWidgetItem(r["code"]))
        num(3, fmt_num(r["price"]), r["price"], True)
        num(4, change_text, change, True)
        num(5, rate_text, rate, True)
        num(6, fmt_num(r["volume"]), r["volume"])
        num(7, fmt_num(r["trade_value"]), r["trade_value"])
        num(8, fmt_num(r["market_cap"]), r["market_cap"])

    def _refresh_summary(self):
        s = self.summary
        if s.get("level") is not None:
            self.level_lbl.setText(f"{s['level']:,.2f}")
            set_label_color(self.level_lbl, INK)
            change, rate = s.get("change") or 0.0, s.get("change_rate") or 0.0
            self.change_lbl.setText(f"{arrow_of(s['direction'])} {abs(change):,.2f}  ({rate:+.2f}%)")
            set_label_color(self.change_lbl, color_of(s["direction"]))
            self.date_lbl.setText(f"기준일 {s.get('date', '')[:10]}")
        else:
            self.level_lbl.setText("0,000.00")
            set_label_color(self.level_lbl, RULE_SOFT)
            self.change_lbl.setText("")
            self.date_lbl.setText("")
        up = sum(1 for r in self.rows if r["direction"] == "up")
        down = sum(1 for r in self.rows if r["direction"] == "down")
        flat = len(self.rows) - up - down
        if self.rows:
            self.up_lbl.setText(f"▲ 상승 {up}")
            self.flat_lbl.setText(f"– 보합 {flat}")
            self.down_lbl.setText(f"▼ 하락 {down}")
        else:
            for lab in (self.up_lbl, self.flat_lbl, self.down_lbl):
                lab.setText("")

    def apply_filter(self):
        key = self.filter_edit.text().strip().casefold()
        shown = 0
        for i in range(self.table.rowCount()):
            name = self.table.item(i, 1).text().casefold()
            code = self.table.item(i, 2).text().casefold()
            hide = bool(key) and key not in name and key not in code
            self.table.setRowHidden(i, hide)
            shown += 0 if hide else 1
        if key and self.rows and not self.thread:
            self.set_status(f"‘{self.filter_edit.text().strip()}’ 검색 결과 {shown}종목 (전체 {len(self.rows)}종목)")

    def _on_done(self, count, message):
        if count == 0:
            self.empty.msg.setText("가져온 종목이 없습니다")
            self.empty.sub.setText(message)
            self.stack.setCurrentWidget(self.empty)
            self.set_status(message)
            return
        latest = max((r["traded_at"] for r in self.rows), default="")
        stamp = f"  ·  기준 {latest[:10]} {latest[11:16]}" if latest else ""
        self.set_status(f"{message}  총 {count}종목{stamp}  ·  더블클릭: 종목 페이지 열기")

    def _on_thread_finished(self):
        self.thread.deleteLater()
        self.worker.deleteLater()
        self.thread = self.worker = None
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.set_running(False)

    def _open_stock(self, item):
        url = self.table.item(item.row(), 1).data(Qt.ItemDataRole.UserRole + 1)
        if url:
            QDesktopServices.openUrl(QUrl(url))

    # ------------------------------------------------------------ 저장
    def _default_name(self, ext):
        return f"kospi200_{datetime.now():%Y%m%d_%H%M}.{ext}"

    def _save(self, title, ext, filter_text, writer):
        path, _ = QFileDialog.getSaveFileName(self, title, self._default_name(ext), filter_text)
        if not path:
            return
        try:
            writer(path)
            self.set_status(f"저장했습니다: {path}")
        except ImportError:
            QMessageBox.critical(self, "엑셀 저장 불가", "엑셀 저장에는 openpyxl 이 필요합니다.\n\npip install openpyxl")
        except OSError as e:
            QMessageBox.critical(self, "저장 실패", f"{e}\n\n같은 이름의 파일이 엑셀 등에서 열려 있으면 저장할 수 없습니다.")

    def save_excel(self):
        self._save("엑셀 저장", "xlsx", "Excel 통합 문서 (*.xlsx)", lambda p: kc.save_xlsx(self.rows, p, self.summary))

    def save_csv(self):
        self._save("CSV 저장", "csv", "CSV (*.csv)", lambda p: kc.save_csv(self.rows, p))

    def save_json(self):
        self._save("JSON 저장", "json", "JSON (*.json)", lambda p: kc.save_json(self.rows, p))

    def closeEvent(self, event):
        if self.thread is not None:
            self.worker.stop()
            self.thread.quit()
            self.thread.wait(15000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    init_fonts()
    app.setFont(make_font(13, serif=False))
    app.setStyleSheet(build_style())
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
