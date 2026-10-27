"""성서유니온 매일성경 오늘의 본문을 가져와 큐티(QT) 노트를 Markdown으로 작성한다.

사용법:
    python scripts/daily_qt.py                 # 오늘 본문을 가져와 Claude 묵상 초안까지 작성
    python scripts/daily_qt.py --no-ai         # 본문 + 빈 묵상 양식만 작성
    python scripts/daily_qt.py --html page.html  # 저장해 둔 HTML로 파싱(테스트용)

환경 변수:
    ANTHROPIC_API_KEY   Claude 묵상 초안 작성에 필요 (--no-ai면 불필요)
    QT_MODEL            사용할 Claude 모델 (기본: claude-opus-5-5)
    QT_INCLUDE_COMMENTARY  "0"이면 성서유니온 해설을 노트에 저장하지 않음 (기본: 1)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://sum.su.or.kr:8888/bible/today"
KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """당신은 성서유니온 '매일성경' 방식(관찰 → 해석 → 적용 → 기도)으로 큐티를 돕는 묵상 도우미입니다.

원칙:
- 오늘 주어진 본문에서 벗어나지 말고, 본문 구절(장:절)을 근거로 인용하세요.
- 해설은 참고만 하고 그대로 베끼지 마세요.
- 정답을 대신 써 주기보다, 사용자가 스스로 묵상할 수 있도록 돕는 초안을 쓰세요.
- 적용은 오늘 하루 실천할 수 있을 만큼 구체적이고 작게 쓰세요.
- 한국어로, 따뜻하고 담백한 문체로 쓰세요.

아래 Markdown 형식만 출력하세요(머리말·맺음말 없이):

## 관찰 (무엇을 말씀하는가)
- 본문의 사건, 인물, 반복되는 표현 등 3~5개 (구절 표기)

## 해석 (하나님은 어떤 분이신가 / 무엇을 의미하는가)
- 2~3개

## 묵상 질문
1. 스스로에게 던질 질문 3개

## 적용 (오늘 나는 어떻게 살 것인가)
- 구체적인 실천 1~2개

## 기도
3~5문장의 기도문

## 오늘의 한 구절
> 마음에 새길 구절 하나 (장:절)
"""


@dataclass
class DailyBible:
    date: str
    title: str = ""
    passage: str = ""
    verses: list[tuple[str, str]] = field(default_factory=list)
    commentary: str = ""
    raw_text: str = ""  # 구조 파싱 실패 시 페이지 본문 텍스트


def fetch_html() -> str:
    resp = requests.get(
        SOURCE_URL,
        headers={"User-Agent": "Mozilla/5.0 (daily-qt-bot)"},
        timeout=30,
    )
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def _text(node) -> str:
    return re.sub(r"[ \t]+", " ", node.get_text("\n", strip=True)) if node else ""


def parse(html: str, date: str) -> DailyBible:
    soup = BeautifulSoup(html, "html.parser")
    bible = DailyBible(date=date)

    bible.title = _text(soup.select_one("#bible_text"))
    passage = re.sub(r"\s+", " ", _text(soup.select_one("#bibleinfo_box")))
    bible.passage = re.sub(r"^본문\s*:\s*", "", passage)

    for li in soup.select("#body_list li"):
        num = _text(li.select_one(".num"))
        info = _text(li.select_one(".info"))
        if info:
            bible.verses.append((num, info))

    bible.commentary = _text(soup.select_one(".body_cont"))

    if not bible.verses:
        # 사이트 구조가 바뀐 경우: 스크립트/스타일을 걷어낸 본문 텍스트를 보관
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        bible.raw_text = _text(soup.body or soup)[:20000]
        if not bible.raw_text:
            raise RuntimeError("본문을 찾지 못했습니다. 사이트 구조가 바뀌었는지 확인하세요.")
    return bible


def scripture_markdown(bible: DailyBible) -> str:
    if bible.verses:
        return "  \n".join(f"**{num}** {info}" if num else info for num, info in bible.verses)
    return bible.raw_text


def write_draft(bible: DailyBible, model: str) -> str:
    import anthropic

    client = anthropic.Anthropic()
    user_content = (
        f"날짜: {bible.date}\n제목: {bible.title}\n본문: {bible.passage}\n\n"
        f"<scripture>\n{scripture_markdown(bible)}\n</scripture>\n\n"
        f"<commentary>\n{bible.commentary}\n</commentary>"
    )
    with client.beta.messages.stream(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        message = stream.get_final_message()

    if message.stop_reason == "refusal":
        raise RuntimeError("Claude가 요청을 거절했습니다.")
    return "\n".join(b.text for b in message.content if b.type == "text").strip()


def render(bible: DailyBible, draft: str | None, include_commentary: bool) -> str:
    lines = [
        f"# {bible.date} 큐티 — {bible.title or '매일성경'}",
        "",
        f"- 본문: {bible.passage or '(확인 필요)'}",
        f"- 출처: [성서유니온 매일성경]({SOURCE_URL})",
        "",
        "## 오늘의 말씀",
        "",
        scripture_markdown(bible),
        "",
    ]
    if include_commentary and bible.commentary:
        lines += [
            "<details>",
            "<summary>성서유니온 해설</summary>",
            "",
            bible.commentary,
            "",
            "</details>",
            "",
        ]
    if draft:
        lines += ["---", "", "> 아래는 Claude가 작성한 묵상 초안입니다. 읽고 고쳐서 나의 묵상으로 만드세요.", "", draft, ""]
    else:
        lines += [
            "---",
            "",
            "## 관찰",
            "- ",
            "",
            "## 해석",
            "- ",
            "",
            "## 적용",
            "- ",
            "",
            "## 기도",
            "",
        ]
    lines += ["## 나의 묵상", "", "_(직접 작성)_", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="성서유니온 매일성경 큐티 노트 자동 작성")
    parser.add_argument("--no-ai", action="store_true", help="Claude 초안 없이 빈 양식만 작성")
    parser.add_argument("--html", type=Path, help="웹 대신 저장된 HTML 파일을 파싱")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "qt", help="노트 저장 폴더")
    parser.add_argument("--force", action="store_true", help="이미 있는 노트를 덮어씀")
    args = parser.parse_args()

    today = datetime.now(KST).date()
    out_path = args.out_dir / f"{today:%Y}" / f"{today:%m}" / f"{today.isoformat()}.md"
    if out_path.exists() and not args.force:
        print(f"이미 작성됨: {out_path} (덮어쓰려면 --force)")
        return 0

    html = args.html.read_text(encoding="utf-8") if args.html else fetch_html()
    bible = parse(html, today.isoformat())

    draft = None
    if not args.no_ai:
        draft = write_draft(bible, os.environ.get("QT_MODEL") or DEFAULT_MODEL)

    include_commentary = os.environ.get("QT_INCLUDE_COMMENTARY", "1") != "0"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(bible, draft, include_commentary), encoding="utf-8")
    print(f"작성 완료: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
