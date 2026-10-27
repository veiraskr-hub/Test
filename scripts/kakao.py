"""오늘 큐티 노트의 '성도 공유글'을 카카오톡 '나에게 보내기'로 전송한다.

사용법:
    python scripts/kakao.py setup --code <인가 코드>   # 최초 1회: 리프레시 토큰 발급·저장
    python scripts/kakao.py send                      # 오늘 공유글 전송
    python scripts/kakao.py send --dry-run            # 전송 없이 보낼 내용만 출력

환경 변수:
    KAKAO_REST_API_KEY    카카오 앱 REST API 키
    KAKAO_CLIENT_SECRET   (선택) 앱에서 Client Secret을 켠 경우
    KAKAO_REFRESH_TOKEN   setup으로 발급된 리프레시 토큰 (send에 필요)
    KAKAO_REDIRECT_URI    (선택) 앱에 등록한 Redirect URI (기본: https://localhost)
    GH_TOKEN              Secret 저장 권한이 있는 GitHub 토큰 (토큰 저장/갱신용)
    QT_NOTE_URL_BASE      메시지 버튼이 열 노트 주소의 앞부분
    KAKAO_TEXT_LIMIT      (선택) 메시지 한 개의 최대 글자 수 (기본 200)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
TOKEN_URL = "https://kauth.kakao.com/oauth/token"
MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
TEXT_LIMIT = int(os.environ.get("KAKAO_TEXT_LIMIT") or 200)  # 텍스트 템플릿 text 최대 길이


def _env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        sys.exit(f"환경 변수 {name}가 필요합니다.")
    return value


def _token_request(data: dict) -> dict:
    data["client_id"] = _env("KAKAO_REST_API_KEY")
    if os.environ.get("KAKAO_CLIENT_SECRET"):
        data["client_secret"] = os.environ["KAKAO_CLIENT_SECRET"]
    resp = requests.post(TOKEN_URL, data=data, timeout=30)
    if resp.status_code != 200:
        sys.exit(f"카카오 토큰 요청 실패 ({resp.status_code}): {resp.text}")
    return resp.json()


def save_refresh_token(token: str) -> None:
    """GitHub Secret KAKAO_REFRESH_TOKEN에 저장한다. 값은 로그에 남기지 않는다."""
    subprocess.run(
        ["gh", "secret", "set", "KAKAO_REFRESH_TOKEN"],
        input=token.encode(),
        check=True,
    )
    print("KAKAO_REFRESH_TOKEN을 저장했습니다.")


def setup(code: str) -> None:
    tokens = _token_request(
        {
            "grant_type": "authorization_code",
            "redirect_uri": os.environ.get("KAKAO_REDIRECT_URI") or "https://localhost",
            "code": code,
        }
    )
    if "talk_message" not in tokens.get("scope", ""):
        sys.exit("'카카오톡 메시지 전송'(talk_message) 동의가 없습니다. 동의항목 설정과 인가 URL의 scope를 확인하세요.")
    save_refresh_token(tokens["refresh_token"])


def share_post(note: Path) -> str:
    text = note.read_text(encoding="utf-8")
    m = re.search(r"^## 성도 공유글\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m or not m.group(1).strip():
        sys.exit(f"'성도 공유글'이 아직 없습니다: {note}")
    return m.group(1).strip()


def split_message(text: str, limit: int = TEXT_LIMIT) -> list[str]:
    """문단 단위로 limit 이하가 되도록 나눈다. 긴 문단은 문장 단위로 나눈다."""
    pieces: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        while len(para) > limit:
            cut = max(para.rfind(sep, 0, limit) for sep in (". ", "? ", "! ", "… ", " "))
            cut = cut + 1 if cut > 0 else limit
            pieces.append(para[:cut].strip())
            para = para[cut:].strip()
        if para:
            pieces.append(para)

    chunks: list[str] = []
    for piece in pieces:
        if chunks and len(chunks[-1]) + 2 + len(piece) <= limit:
            chunks[-1] += "\n\n" + piece
        else:
            chunks.append(piece)
    return chunks


def send(dry_run: bool) -> None:
    today = datetime.now(KST).date()
    rel = f"qt/{today:%Y}/{today:%m}/{today.isoformat()}.md"
    chunks = split_message(share_post(ROOT / rel))

    if dry_run:
        for i, chunk in enumerate(chunks, 1):
            print(f"--- {i}/{len(chunks)} ({len(chunk)}자)\n{chunk}")
        return

    if not os.environ.get("KAKAO_REFRESH_TOKEN"):
        print("KAKAO_REFRESH_TOKEN이 없어 전송을 건너뜁니다. README의 카카오톡 설정을 먼저 진행하세요.")
        return

    tokens = _token_request({"grant_type": "refresh_token", "refresh_token": os.environ["KAKAO_REFRESH_TOKEN"]})
    if tokens.get("refresh_token"):
        # 만료 1개월 전부터 새 리프레시 토큰이 함께 발급된다
        save_refresh_token(tokens["refresh_token"])

    url = f"{_env('QT_NOTE_URL_BASE').rstrip('/')}/{rel}"
    link = {"web_url": url, "mobile_web_url": url}
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    for i, chunk in enumerate(chunks, 1):
        template = {"object_type": "text", "text": chunk, "link": link, "button_title": "노트 보기"}
        resp = requests.post(
            MEMO_URL,
            headers=headers,
            data={"template_object": json.dumps(template, ensure_ascii=False)},
            timeout=30,
        )
        if resp.status_code != 200 or resp.json().get("result_code") != 0:
            sys.exit(f"카카오톡 전송 실패 ({i}/{len(chunks)}, {resp.status_code}): {resp.text}")
    print(f"카카오톡으로 공유글을 보냈습니다 ({len(chunks)}개 메시지).")


def main() -> None:
    parser = argparse.ArgumentParser(description="큐티 공유글 카카오톡 전송")
    sub = parser.add_subparsers(dest="command", required=True)
    p_setup = sub.add_parser("setup", help="인가 코드로 리프레시 토큰 발급·저장")
    p_setup.add_argument("--code", required=True)
    p_send = sub.add_parser("send", help="오늘 공유글 전송")
    p_send.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.command == "setup":
        setup(args.code)
    else:
        send(args.dry_run)


if __name__ == "__main__":
    main()
