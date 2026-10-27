# 매일성경 큐티 자동화

[성서유니온 매일성경](https://sum.su.or.kr:8888/bible/today)의 오늘 본문을 가져와서
Claude가 묵상 초안(관찰 · 해석 · 묵상 질문 · 적용 · 기도)을 쓰고,
`qt/YYYY/MM/YYYY-MM-DD.md` 노트로 이 저장소에 커밋합니다.

초안 아래의 **나의 묵상** 칸은 직접 채워서 노트를 완성하면 됩니다.

## 설정

1. 저장소 **Settings → Secrets and variables → Actions**에서 Secret `ANTHROPIC_API_KEY`를 추가합니다.
2. (선택) 같은 화면의 **Variables** 탭:
   - `QT_MODEL`: 사용할 모델 (기본 `claude-opus-5-5`)
   - `QT_INCLUDE_COMMENTARY`: `0`이면 성서유니온 해설을 노트에 저장하지 않습니다.
3. **Actions → Daily QT → Run workflow**로 바로 한 번 실행해 봅니다.
   이후에는 매일 05:47(KST)에 자동으로 실행됩니다.

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
