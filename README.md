# 매일성경 큐티 자동화

[성서유니온 매일성경](https://sum.su.or.kr:8888/bible/today)의 오늘 본문을 가져와서
Claude가 묵상 초안(관찰 · 해석 · 묵상 질문 · 적용 · 기도)을 써서
`qt/YYYY/MM/YYYY-MM-DD.md` 노트로 이 저장소에 커밋합니다.

초안 아래의 **나의 묵상** 칸은 직접 채워서 노트를 완성하면 됩니다.

## 매일 동작 순서

1. **04:17 (KST)** GitHub Actions가 오늘 본문을 받아 빈 묵상 양식 노트를 커밋합니다.
   사이트가 응답하지 않으면 05:17, 06:17에 다시 시도합니다(노트가 생긴 뒤에는 건너뜀).
2. **04:51 (KST)** Claude Code 예약 작업이 그 노트를 읽고 `prompts/qt_draft.md` 형식대로
   묵상 초안을 채워 커밋합니다. 노트가 아직 없으면 워크플로를 직접 실행해 보고,
   그래도 없으면 05:51, 06:51에 다시 시도합니다. (API 키 없이 Claude 구독 사용량으로 동작합니다.)
3. 초안이 커밋되면 **성도 공유글**이 카카오톡으로 전송됩니다(아래 설정 필요).
4. 아침에 노트를 열어 **나의 묵상** 칸을 채웁니다.

초안 형식을 바꾸고 싶으면 `prompts/qt_draft.md`를 고치면 됩니다.

### (선택) API 키로 Actions에서 바로 초안 작성

Secret `ANTHROPIC_API_KEY`를 등록하면 1단계에서 초안까지 작성합니다. 키가 없으면 빈 양식만 만듭니다.
Variables: `QT_MODEL`(기본 `claude-opus-5-5`), `QT_INCLUDE_COMMENTARY`(`0`이면 해설 저장 안 함).

## 카카오톡으로 공유글 받기

Claude가 초안을 커밋하면(`QT draft:` 커밋) GitHub Actions가 노트의 **성도 공유글**만
카카오톡 **나에게 보내기**로 전송합니다. 텍스트 메시지 길이 제한(200자) 때문에 문단 단위로
2~4개 메시지로 나뉘어 옵니다(`KAKAO_TEXT_LIMIT` 변수로 조정). 설정 전에는 전송을 건너뜁니다.

### 최초 설정 (1회)

1. [Kakao Developers](https://developers.kakao.com) → **내 애플리케이션 → 애플리케이션 추가**.
2. **앱 키**에서 **REST API 키**를 복사합니다.
3. **카카오 로그인**을 활성화하고 **Redirect URI**에 `https://localhost`를 등록합니다.
4. **동의항목**에서 **카카오톡 메시지 전송(talk_message)**을 선택 동의로 설정합니다.
   (보안 메뉴에서 Client Secret을 켰다면 그 값도 복사해 둡니다.)
5. GitHub **Settings → Developer settings → Fine-grained tokens**에서 이 저장소만 선택하고
   **Secrets: Read and write** 권한을 준 토큰을 만듭니다. (카카오 토큰을 Secret에 저장·자동 갱신하는 데 씁니다.)
6. 저장소 **Settings → Secrets and variables → Actions**에 Secret을 추가합니다:
   `KAKAO_REST_API_KEY`, `GH_PAT`(5번 토큰), (켰다면) `KAKAO_CLIENT_SECRET`.
7. 휴대폰이나 PC 브라우저에서 아래 주소를 엽니다(`REST_API_키` 부분을 바꿔서).
   `https://kauth.kakao.com/oauth/authorize?client_id=REST_API_키&redirect_uri=https://localhost&response_type=code&scope=talk_message`
   로그인·동의하면 `https://localhost/?code=...` 페이지로 이동하며 "연결할 수 없음"이 뜨는데 정상입니다.
   주소창의 `code=` 뒤 값을 복사합니다(10분 안에 다음 단계 진행).
8. **Actions → Kakao Setup → Run workflow**에 그 코드를 넣고 실행합니다.
9. **Actions → Send QT to KakaoTalk → Run workflow**로 오늘 공유글이 오는지 확인합니다.

리프레시 토큰은 약 2개월 유효하며, 매일 전송할 때 자동으로 갱신됩니다.

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
