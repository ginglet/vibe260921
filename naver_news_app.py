"""네이버 뉴스 크롤러 - PyQt6 GUI 앱 (에디토리얼 / 신문 스타일)

크롤링 로직은 naver_news_crawler.py 를 그대로 재사용합니다. (같은 폴더에 두세요)

실행
  pip install PyQt6 requests beautifulsoup4 openpyxl
  python naver_news_app.py

사용법
  1) 검색어(예: 반도체)를 입력하고 [수집 시작] 또는 Enter를 누릅니다. 네이버 검색 결과 URL을 붙여넣어도 됩니다.
  2) 왼쪽 목차에서 기사를 고르면 오른쪽에 신문 기사처럼 본문이 표시됩니다. (더블클릭: 원문 열기)
  3) [엑셀 저장] / [CSV 저장] / [JSON 저장]으로 결과를 파일로 내보냅니다.

주의: 네이버 robots.txt 와 약관은 자동 수집을 제한합니다. 학습·개인 연구용으로 소량만 사용하고,
      기사(저작권은 각 언론사에 있음)를 재배포하거나 AI 학습에 쓰지 마세요. 자세한 내용은 naver_news_crawler.py 참고.
"""
import csv
import html
import json
import random
import re
import sys
import time
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import requests
from PyQt6.QtCore import QObject, QRect, QSize, Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QPainter, QPen, QTextDocument
from PyQt6.QtWidgets import (
    QApplication, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListView, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QProgressBar, QPushButton, QSizePolicy,
    QSpinBox, QSplitter, QStyle, QStyledItemDelegate, QTextBrowser, QVBoxLayout, QWidget,
)

import naver_news_crawler as crawler

# ---------------------------------------------------------------- 디자인 토큰 (종이 + 잉크 + 붉은 포인트)
PAPER = "#F3EEE3"
PAPER_LIGHT = "#FAF7F0"
PAPER_DARK = "#E9E2D2"
INK = "#16130F"
MUTED = "#6B645A"
RULE_SOFT = "#CFC7B7"
ACCENT = "#A4262C"

SERIF = "Georgia"
SANS = "Malgun Gothic"

WEEKDAYS = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


def pick_font(candidates, default):
    have = set(QFontDatabase.families())
    return next((c for c in candidates if c in have), default)


def init_fonts():
    """설치된 글꼴 중 신문 느낌의 명조(세리프) / 고딕 글꼴을 고른다."""
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


def label(text, size, *, bold=False, italic=False, color=INK, spacing=0.0, serif=True, align=None, wrap=False):
    lab = QLabel(text)
    lab.setFont(make_font(size, bold=bold, italic=italic, spacing=spacing, serif=serif))
    lab.setStyleSheet(f"color:{color}; background:transparent;")
    lab.setWordWrap(wrap)
    if align is not None:
        lab.setAlignment(align)
    return lab


def rule(height=1, color=INK):
    line = QFrame()
    line.setFixedHeight(height)
    line.setStyleSheet(f"background:{color}; border:none;")
    return line


def keyword_of(text):
    """입력값에서 검색어를 뽑는다. URL이면 query= 값을, 아니면 입력한 글자 그대로."""
    text = (text or "").strip()
    if not re.match(r"^https?://", text, re.IGNORECASE):
        return text
    try:
        return parse_qs(urlparse(text).query).get("query", [""])[0]
    except ValueError:
        return ""


def fmt_published(s):
    try:
        d = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return f"{d.year}.{d.month:02d}.{d.day:02d} {d:%H:%M}"
    except (TypeError, ValueError):
        return s or ""


def esc(s):
    return html.escape(s or "")


# ---------------------------------------------------------------- 크롤링 작업 스레드
class CrawlWorker(QObject):
    article = pyqtSignal(dict)
    progress = pyqtSignal(int, int)      # 처리한 링크 수, 전체 링크 수
    status = pyqtSignal(str)
    done = pyqtSignal(int, str)          # 수집한 기사 수, 종료 메시지

    def __init__(self, url, limit, delay):
        super().__init__()
        self.url, self.limit, self.delay = url, limit, delay
        self._stop = False

    def stop(self):
        self._stop = True

    def _sleep(self, seconds):
        end = time.monotonic() + seconds
        while not self._stop and time.monotonic() < end:
            time.sleep(0.05)

    def run(self):
        collected = 0
        try:
            session = requests.Session()
            session.headers.update(crawler.HEADERS)

            self.status.emit("검색 결과 페이지를 가져오는 중…")
            page = crawler.fetch(session, self.url, log=self.status.emit)
            if page is None:
                self.done.emit(0, "검색 결과 페이지를 가져오지 못했습니다. 네트워크와 주소를 확인해 주세요.")
                return
            links = crawler.extract_article_links(page)[: self.limit]
            if not links:
                self.done.emit(0, "네이버 뉴스 형식의 기사를 찾지 못했습니다. 다른 검색어를 시도해 보세요.")
                return

            total = len(links)
            for i, link in enumerate(links):
                if self._stop:
                    break
                if i:
                    self._sleep(self.delay + random.uniform(0, 0.7))     # 서버 부담을 줄이기 위한 대기
                    if self._stop:
                        break
                self.status.emit(f"기사 {i + 1} / {total} 를 읽는 중…")
                body = crawler.fetch(session, link, log=self.status.emit)
                article = crawler.parse_article(body, link) if body else None
                if article:
                    collected += 1
                    self.article.emit(article)
                else:
                    self.status.emit(f"기사 {i + 1} 은(는) 건너뜁니다. (가져오기 실패 또는 지원하지 않는 형식)")
                self.progress.emit(i + 1, total)
            self.done.emit(collected, "수집을 중지했습니다." if self._stop else "수집을 마쳤습니다.")
        except Exception as e:      # 스레드 안의 예외가 앱을 죽이지 않도록
            self.done.emit(collected, f"오류가 발생했습니다: {e}")


# ---------------------------------------------------------------- 목차(기사 목록) 그리기
class ContentsDelegate(QStyledItemDelegate):
    """번호 · 언론사/시각 · 헤드라인을 신문 목차처럼 그린다."""
    NUM_W = 58
    PAD_TOP = 14

    def __init__(self, view):
        super().__init__(view)
        self.view = view

    def _doc(self, article, width):
        doc = QTextDocument()
        doc.setDefaultFont(make_font(15, serif=True))
        doc.setTextWidth(max(80, width))
        meta = f"{esc(article['press'])}  ·  {esc(fmt_published(article['published']))}"
        doc.setHtml(
            f"<div style='font-family:\"{SANS}\"; font-size:11px; color:{ACCENT};'>{meta}</div>"
            f"<div style='font-size:16px; font-weight:600; color:{INK}; line-height:100%;'>{esc(article['title'])}</div>"
        )
        return doc

    def _text_width(self):
        return self.view.viewport().width() - self.NUM_W - 18

    def sizeHint(self, option, index):
        doc = self._doc(index.data(Qt.ItemDataRole.UserRole), self._text_width())
        return QSize(self.view.viewport().width(), int(doc.size().height()) + self.PAD_TOP * 2 + 1)

    def paint(self, painter, option, index):
        article = index.data(Qt.ItemDataRole.UserRole)
        r = option.rect
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.fillRect(r, QColor(PAPER_DARK if selected else (PAPER_LIGHT if hovered else PAPER)))
        if selected:
            painter.fillRect(QRect(r.left(), r.top(), 4, r.height()), QColor(ACCENT))

        painter.setFont(make_font(26, bold=False, italic=True))
        painter.setPen(QColor(ACCENT if selected else "#B9B0A0"))
        painter.drawText(QRect(r.left() + 16, r.top() + self.PAD_TOP - 4, self.NUM_W - 16, 36),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, f"{index.row() + 1:02d}")

        painter.translate(r.left() + self.NUM_W, r.top() + self.PAD_TOP)
        self._doc(article, self._text_width()).drawContents(painter)
        painter.restore()

        painter.save()
        painter.setPen(QPen(QColor(RULE_SOFT), 1))
        painter.drawLine(r.left() + 16, r.bottom(), r.right() - 16, r.bottom())
        painter.restore()


# ---------------------------------------------------------------- 기사 본문(리더) HTML
def article_html(a):
    paras = [p for p in a["body"].split("\n") if p.strip()]
    lead = paras[0] if paras else ""
    rest = paras[1:]
    byline = " · ".join(x for x in [a["reporter"]] if x)
    parts = [
        f"<div style='font-family:\"{SANS}\"; font-size:12px; color:{ACCENT}; letter-spacing:3px;'>"
        f"{esc(a['press']).upper()} &nbsp;/&nbsp; {esc(fmt_published(a['published']))}</div>",
        f"<p style='font-size:34px; font-weight:700; line-height:100%; margin:10px 0 12px 0; color:{INK};'>{esc(a['title'])}</p>",
    ]
    if byline:
        parts.append(f"<p style='font-style:italic; font-size:14px; color:{MUTED}; margin:0 0 14px 0;'>{esc(byline)}</p>")
    parts.append(f"<hr style='background-color:{INK}; border-width:0; height:2px;'>")
    if lead:
        parts.append(f"<p style='font-size:19px; line-height:115%; margin:18px 0 16px 0; color:{INK};'>{esc(lead)}</p>")
    for p in rest:
        parts.append(f"<p style='font-size:16px; line-height:120%; margin:0 0 14px 0; text-align:justify; color:#2A251E;'>{esc(p)}</p>")
    parts.append(f"<hr style='background-color:{RULE_SOFT}; border-width:0; height:1px;'>")
    parts.append(f"<p style='font-family:\"{SANS}\"; font-size:12px; margin-top:12px;'>"
                 f"<a href='{esc(a['url'])}' style='color:{ACCENT}; text-decoration:none;'>네이버 뉴스에서 원문 보기 →</a></p>")
    return f"<div style='font-family:\"{SERIF}\";'>{''.join(parts)}</div>"


def empty_html(message, sub=""):
    return (f"<div style='font-family:\"{SERIF}\"; text-align:center; margin-top:120px; color:{MUTED};'>"
            f"<p style='font-size:40px; margin:0; color:{RULE_SOFT};'>§</p>"
            f"<p style='font-size:20px; font-style:italic; margin:10px 0 6px 0;'>{esc(message)}</p>"
            f"<p style='font-family:\"{SANS}\"; font-size:12px; margin:0;'>{esc(sub)}</p></div>")


STYLE = """
QWidget#root { background: @PAPER; }
QMainWindow { background: @PAPER; }
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
QListWidget { background: @PAPER; border: none; outline: 0; }
QTextBrowser { background: @PAPER_LIGHT; border: none; padding: 30px 52px; selection-background-color: @ACCENT; selection-color: @PAPER; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: @RULE_SOFT; min-height: 36px; }
QScrollBar::handle:vertical:hover { background: @MUTED; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QSplitter::handle { background: @INK; }
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


# ---------------------------------------------------------------- 메인 창
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("뉴스 크롤러 — 네이버 뉴스 수집")
        self.resize(1240, 820)
        self.setMinimumSize(980, 640)

        self.articles = []
        self.thread = None
        self.worker = None

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(36, 18, 36, 14)
        layout.setSpacing(0)

        layout.addWidget(self._build_masthead())
        layout.addSpacing(14)
        layout.addLayout(self._build_controls())
        layout.addSpacing(14)
        layout.addWidget(rule(1))
        layout.addWidget(self._build_body(), 1)
        layout.addLayout(self._build_footer())

        self.query_edit.textChanged.connect(self._update_keyword)
        self._update_keyword()
        self.reader.setHtml(empty_html("수집한 기사가 여기에 실립니다", "‘수집 시작’을 눌러 오늘의 기사를 가져오세요."))

    # ------------------------------------------------------------ UI 구성
    def _build_masthead(self):
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        v.addWidget(rule(1))
        v.addSpacing(6)

        now = datetime.now()
        date_text = f"{now.year}년 {now.month}월 {now.day}일 {WEEKDAYS[now.weekday()]}"
        top = QGridLayout()
        top.setContentsMargins(0, 0, 0, 0)
        for col in range(3):
            top.setColumnStretch(col, 1)
        top.addWidget(label(date_text, 12, serif=False, color=MUTED, spacing=0.5), 0, 0, Qt.AlignmentFlag.AlignLeft)
        top.addWidget(label("NAVER NEWS  ·  DAILY EDITION", 10, bold=True, serif=False, color=MUTED, spacing=3),
                      0, 1, Qt.AlignmentFlag.AlignCenter)
        self.keyword_lbl = label("", 12, italic=True, color=ACCENT)
        top.addWidget(self.keyword_lbl, 0, 2, Qt.AlignmentFlag.AlignRight)
        v.addLayout(top)

        v.addSpacing(2)
        v.addWidget(label("뉴스 크롤러", 54, bold=True, spacing=10, align=Qt.AlignmentFlag.AlignCenter))
        v.addWidget(label("검색 결과 속 기사를 한 장의 신문처럼 모아 읽습니다", 13, italic=True, color=MUTED,
                          align=Qt.AlignmentFlag.AlignCenter))
        v.addSpacing(10)
        v.addWidget(rule(3))
        v.addSpacing(3)
        v.addWidget(rule(1))
        return box

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

        self.query_edit = QLineEdit("반도체")
        self.query_edit.setFont(make_font(17, serif=True))
        self.query_edit.setPlaceholderText("검색어를 입력하세요  (예: 반도체, 전기차 보조금)  ·  검색 결과 URL도 가능")
        self.query_edit.returnPressed.connect(self.start)

        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 30)
        self.limit_spin.setValue(10)
        self.limit_spin.setSuffix(" 건")
        self.limit_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.limit_spin.setFont(make_font(15, serif=True))

        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(1.0, 10.0)
        self.delay_spin.setSingleStep(0.5)
        self.delay_spin.setValue(1.0)
        self.delay_spin.setDecimals(1)
        self.delay_spin.setSuffix(" 초")
        self.delay_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.delay_spin.setFont(make_font(15, serif=True))
        self.delay_spin.setToolTip("기사 요청 사이 최소 대기 시간입니다. 서버에 부담을 주지 않도록 1초 이상만 허용합니다.")

        self.start_btn = QPushButton("수집 시작")
        self.start_btn.setObjectName("primary")
        self.stop_btn = QPushButton("중지")
        self.stop_btn.setObjectName("ghost")
        for b in (self.start_btn, self.stop_btn):
            b.setFont(make_font(13, bold=True, spacing=1.5, serif=False))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)

        row.addWidget(self._field("검색어  KEYWORD  (또는 검색 URL)", self.query_edit), 1)
        row.addWidget(self._field("기사 수  ARTICLES", self.limit_spin, 120))
        row.addWidget(self._field("대기  DELAY", self.delay_spin, 100))
        row.addWidget(self.start_btn, 0, Qt.AlignmentFlag.AlignBottom)
        row.addWidget(self.stop_btn, 0, Qt.AlignmentFlag.AlignBottom)
        return row

    def _build_body(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        # 왼쪽: 목차
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)
        head = QHBoxLayout()
        head.setContentsMargins(16, 12, 16, 10)
        head.addWidget(label("목차  CONTENTS", 11, bold=True, serif=False, spacing=3))
        head.addStretch()
        self.count_lbl = label("0건", 12, italic=True, color=MUTED)
        head.addWidget(self.count_lbl)
        lv.addLayout(head)
        lv.addWidget(rule(1))

        self.list = QListWidget()
        self.list.setResizeMode(QListView.ResizeMode.Adjust)
        self.list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setMouseTracking(True)
        self.list.setItemDelegate(ContentsDelegate(self.list))
        self.list.currentRowChanged.connect(self._show_article)
        self.list.itemDoubleClicked.connect(
            lambda item: QDesktopServices.openUrl(QUrl(item.data(Qt.ItemDataRole.UserRole)["url"])))
        lv.addWidget(self.list, 1)
        left.setMinimumWidth(340)

        # 오른쪽: 기사 읽기
        self.reader = QTextBrowser()
        self.reader.setOpenExternalLinks(True)
        self.reader.setFrameShape(QFrame.Shape.NoFrame)

        splitter.addWidget(left)
        splitter.addWidget(self.reader)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 800])
        return splitter

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
        self.status_lbl = label("준비되었습니다.", 13, italic=True, color=MUTED)
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
            b.clicked.connect(fn)
            row.addWidget(b)
        v.addLayout(row)
        return v

    # ------------------------------------------------------------ 동작
    def _update_keyword(self):
        kw = keyword_of(self.query_edit.text())
        self.keyword_lbl.setText(f"오늘의 검색어 — {kw}" if kw else "")

    def set_status(self, text):
        self.status_lbl.setText(text)

    def set_running(self, running):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.query_edit.setReadOnly(running)
        self.limit_spin.setEnabled(not running)
        self.delay_spin.setEnabled(not running)
        can_save = bool(self.articles) and not running
        for b in self.save_buttons:
            b.setEnabled(can_save)

    def start(self):
        if self.thread is not None:
            return
        url = crawler.build_search_url(self.query_edit.text())     # 검색어 → 검색 URL (URL은 그대로)
        if not url:
            QMessageBox.information(self, "검색어 확인", "검색어를 입력해 주세요.  예) 반도체")
            self.query_edit.setFocus()
            return

        self.articles.clear()
        self.list.clear()
        self._update_count()
        self.progress.setValue(0)
        self.reader.setHtml(empty_html("기사를 가져오는 중입니다…", "잠시만 기다려 주세요."))

        self.thread = QThread(self)
        self.worker = CrawlWorker(url, self.limit_spin.value(), self.delay_spin.value())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.article.connect(self.add_article)
        self.worker.progress.connect(self._on_progress)
        self.worker.status.connect(self.set_status)
        self.worker.done.connect(self._on_done)
        self.worker.done.connect(self.thread.quit)
        self.thread.finished.connect(self._on_thread_finished)
        self.set_running(True)
        self.set_status(f"‘{keyword_of(self.query_edit.text())}’ 검색 결과에서 수집을 시작합니다…")
        self.thread.start()

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.stop_btn.setEnabled(False)
            self.set_status("중지하는 중… (진행 중인 요청이 끝나면 멈춥니다)")

    def add_article(self, article):
        self.articles.append(article)
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, article)
        self.list.addItem(item)
        self._update_count()
        if self.list.currentRow() < 0:
            self.list.setCurrentRow(0)

    def _on_progress(self, done, total):
        self.progress.setMaximum(total)
        self.progress.setValue(done)

    def _on_done(self, count, message):
        self.set_status(f"{message}  총 {count}건")
        if count == 0:
            self.reader.setHtml(empty_html("수집된 기사가 없습니다", message))

    def _on_thread_finished(self):
        self.thread.deleteLater()
        self.worker.deleteLater()
        self.thread = self.worker = None
        self.set_running(False)

    def _update_count(self):
        self.count_lbl.setText(f"{len(self.articles)}건")

    def _show_article(self, row):
        if 0 <= row < len(self.articles):
            self.reader.setHtml(article_html(self.articles[row]))
            self.reader.verticalScrollBar().setValue(0)

    # ------------------------------------------------------------ 저장
    def _default_name(self, ext):
        kw = re.sub(r"[^\w가-힣-]+", "_", keyword_of(self.query_edit.text())) or "news"
        return f"naver_news_{kw}_{datetime.now():%Y%m%d_%H%M}.{ext}"

    def save_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "엑셀 저장", self._default_name("xlsx"), "Excel 통합 문서 (*.xlsx)")
        if not path:
            return
        try:
            crawler.save_xlsx(self.articles, path)
            self.set_status(f"엑셀로 저장했습니다: {path}")
        except ImportError:
            QMessageBox.critical(self, "엑셀 저장 불가", "엑셀 저장에는 openpyxl 이 필요합니다.\n\npip install openpyxl")
        except OSError as e:
            QMessageBox.critical(self, "저장 실패", f"{e}\n\n같은 이름의 파일이 엑셀에서 열려 있으면 저장할 수 없습니다.")

    def save_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "JSON 저장", self._default_name("json"), "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.articles, f, ensure_ascii=False, indent=2)
            self.set_status(f"저장했습니다: {path}")
        except OSError as e:
            QMessageBox.critical(self, "저장 실패", str(e))

    def save_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "CSV 저장", self._default_name("csv"), "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:      # 엑셀에서 한글이 깨지지 않도록 BOM 포함
                writer = csv.DictWriter(f, fieldnames=list(self.articles[0].keys()))
                writer.writeheader()
                writer.writerows(self.articles)
            self.set_status(f"저장했습니다: {path}")
        except OSError as e:
            QMessageBox.critical(self, "저장 실패", str(e))

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
