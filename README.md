# 매일성경 큐티 자동화

[성서유니온 매일성경](https://sum.su.or.kr:8888/bible/today)의 오늘 본문을 가져와서
Claude가 묵상 초안(관찰 · 해석 · 묵상 질문 · 적용 · 기도)을 써서
`qt/YYYY/MM/YYYY-MM-DD.md` 노트로 이 저장소에 커밋합니다.

초안 아래의 **나의 묵상** 칸은 직접 채워서 노트를 완성하면 됩니다.

## 매일 동작 순서

1. **04:17 (KST)** GitHub Actions가 오늘 본문을 받아 빈 묵상 양식 노트를 커밋합니다.
2. **04:51 (KST)** Claude Code 예약 작업이 그 노트를 읽고 `prompts/qt_draft.md` 형식대로
   묵상 초안을 채워 커밋합니다. 노트가 아직 없으면 워크플로를 직접 실행한 뒤 이어서 작성합니다.
   (API 키 없이 Claude 구독 사용량으로 동작합니다.)
3. 아침에 노트를 열어 **나의 묵상** 칸을 채웁니다.

초안 형식을 바꾸고 싶으면 `prompts/qt_draft.md`를 고치면 됩니다.

### (선택) API 키로 Actions에서 바로 초안 작성

Secret `ANTHROPIC_API_KEY`를 등록하면 1단계에서 초안까지 작성합니다. 키가 없으면 빈 양식만 만듭니다.
Variables: `QT_MODEL`(기본 `claude-opus-5-5`), `QT_INCLUDE_COMMENTARY`(`0`이면 해설 저장 안 함).

## 로컬에서 실행

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python scripts/daily_qt.py            # 본문 + Claude 묵상 초안
python scripts/daily_qt.py --no-ai    # 본문 + 빈 묵상 양식
python scripts/daily_qt.py --force    # 오늘 노트를 다시 작성
```

## 참고

- 매일성경 본문과 해설의 저작권은 성서유니온선교회에 있습니다.
  저장소를 공개(public)로 두면 해설까지 공개되므로, 비공개로 두거나 `QT_INCLUDE_COMMENTARY=0`을 쓰세요.
- 사이트 HTML 구조가 바뀌면 `scripts/daily_qt.py`의 `parse()` 선택자를 고쳐야 합니다.
  구조를 못 찾으면 페이지 전체 텍스트를 본문 자리에 넣고, Claude는 그 텍스트를 바탕으로 초안을 씁니다.
