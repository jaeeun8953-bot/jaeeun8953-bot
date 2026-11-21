# 박재은 | 개인정보보호 · 서비스 구현

동의서의 고지·동의 요건을 검토 기준으로 구체화하고, 검출 방식을 직접 구현해 오탐과 미탐이 발생하는 조건을 분석했습니다. Gemini API와 Streamlit을 활용한 웹 서비스도 기획·구현·배포했습니다.

## 개인정보 이용동의서 위험조항 자동 검출

**2023 융합보안 창의·소프트웨어경진대회 우수상**

- 개인정보 수집·이용과 제3자 제공 시 필수 고지 항목, 아동의 법정대리인 동의, 별도 동의 요건을 문장별 검토 기준으로 정리했습니다.
- 안전 문장 1,000개와 위험 문장 1,000개를 구축하고, 유사도 기반 검출과 GPT API 기반 판단을 각각 구현했습니다.
- 기존 목록에 없던 유형을 100문장씩 두 차례 추가해 재검증했습니다.

| 평가 항목 | 유사도 기반 | GPT API 기반 |
| --- | ---: | ---: |
| 초기 정확도 | 68.78% | 76.05% |
| 신규 유형 200문장 추가 후 정확도 | 59.70% | 72.65% |
| 문장당 평균 처리 시간 | 0.02초 | 59초 |

임계값에 따른 오탐·미탐 조건을 분석하고, 유사도로 검토 대상을 먼저 선별한 뒤 GPT로 정밀 검토하는 방식을 개선안으로 제안했습니다.

## 서비스 프로젝트

### 망상회로
이전 선택을 반영해 생각을 확장할 방향을 제안하는 AI 웹 서비스입니다. Gemini API와 Streamlit으로 구현·배포하고, API 호출 한도와 응답 오류에 캐싱·예외처리를 적용했습니다.

<img src="assets/mangsang.png" alt="망상회로의 아이디어 확장 제안 화면" width="290">

[서비스 체험](https://mangsang-circuit.streamlit.app/) · [코드](https://github.com/jaeeun8953-bot/mangsang)

### 스토리오븐
어린이가 소재, 캐릭터, 사건을 선택하며 이야기를 완성하는 AI 창작 앱입니다.

[서비스 체험](https://mashmellow-teller-am8gp9ddwvdoh4cedxu3w7.streamlit.app/) · [코드](https://github.com/jaeeun8953-bot/mashmellow-teller)

### TPOWI 2.0
냉장고에 보유한 재료를 등록하고, 그 재료로 만들 수 있는 메뉴를 추천받는 앱입니다.

[서비스 체험](https://tpowi-your-smart-fridge-9yeg4zz5k2tfsdvibslxxj.streamlit.app/) · [코드](https://github.com/jaeeun8953-bot/TPOWI-Your-Smart-Fridge)

### 수면 유도 화이트비치
보라카이 해변을 테마로 한 휴식용 웹 앱입니다. 모래성을 만들고 진행 상태를 저장할 수 있습니다.

 [서비스 체험](https://sleeping-borakay-qjh9x4eowxcffxwktsyvn9.streamlit.app/) ·[코드](https://github.com/jaeeun8953-bot/Sleeping-Beauty)
