"""Pilot evaluation of staged similarity and GPT-5."""
import csv
from hashlib import sha256
from io import StringIO
from pathlib import Path
from statistics import mean
from time import perf_counter
from urllib.error import HTTPError

import altair as alt
import pandas as pd
import streamlit as st

from model_study import BATCH_SIZE, STUDY_MODEL, measure_batch, summarize
from similarity import BLACK, WHITE, classify, reference_vectors, score

THRESHOLDS = (20, 40, 60, 80)
SIMILARITY = "TF-IDF + 코사인 유사도"
GPT = "GPT-5"


def measure_similarity(sentence):
    start = perf_counter()
    white, black, white_match, black_match = score([sentence])[0]
    predictions = {f"유사도 {percent}%": classify(white, black, percent / 100, percent / 100)
                   for percent in THRESHOLDS}
    return {
        **predictions, "유사도 시간(초)": perf_counter() - start,
        "화이트 최고": white, "블랙 최고": black,
        "화이트 근접 표현": white_match, "블랙 근접 표현": black_match,
    }


def metrics(frame, method):
    pred = frame[method]
    truth = frame["정답"]
    counts = summarize([{"정답": row["정답"], "예측": row[method], "응답 시간(초)": row["GPT 시간(초)" if method == "GPT" else "유사도 시간(초)"]}
                        for row in frame.to_dict("records")])
    counts["미탐"] += int(((truth == "위험") & (pred == "판단 유보")).sum())
    counts["유보"] = int((pred == "판단 유보").sum())
    return counts


def average_similarity(frame):
    per_threshold = [metrics(frame, f"유사도 {percent}%") for percent in THRESHOLDS]
    return {field: mean(result[field] for result in per_threshold) for field in per_threshold[0]}


st.set_page_config(page_title="개인정보 동의서 후속연구", layout="wide")
st.title("개인정보 동의서 위험 문장 검증")
st.caption("새 가상 문장 2,000개에서 화이트리스트 → 블랙리스트 기반 TF-IDF·코사인 유사도와 GPT-5를 비교해요.")
data = Path(__file__).with_name("followup_samples_2000.csv").read_bytes()
examples = list(csv.DictReader(StringIO(data.decode("utf-8-sig"), newline="")))
st.download_button("검증 데이터 2,000개 CSV", data, "followup_samples_2000.csv", mime="text/csv")
with st.expander("검증 데이터와 기준 목록"):
    st.write("10개 유형을 200문장씩 묶었어요. 각 유형은 20개 상황과 5개 신청 경로를 조합해 안전 100문장, 위험 100문장으로 구성했어요.")
    st.dataframe(pd.DataFrame(examples).groupby(["category", "label"]).size().unstack().reset_index().rename(columns={"category": "유형"}), hide_index=True)
    a, b = st.columns(2)
    a.write("화이트리스트 · 100개")
    a.dataframe(pd.DataFrame({"기준 표현": WHITE}), hide_index=True)
    b.write("블랙리스트 · 100개")
    b.dataframe(pd.DataFrame({"기준 표현": BLACK}), hide_index=True)

session_key = (sha256(data).hexdigest(), STUDY_MODEL, "batch200")
if st.session_state.get("pilot_source") != session_key:
    st.session_state.pilot_source = session_key
    st.session_state.pilot_results = []
results = st.session_state.pilot_results
st.caption("유사도 정확도는 화이트·블랙 공통 임계값 20·40·60·80%에서 각각 채점한 뒤 네 값의 평균으로 표시해요.")
progress = st.progress(len(results) / len(examples), text=f"{len(results)}/{len(examples)}문장 검증 완료")
if len(results) < len(examples):
    count = min(BATCH_SIZE - len(results) % BATCH_SIZE, len(examples) - len(results))
    category = examples[len(results)]["category"]
    st.caption("가상 문장 200개를 GPT-5 API 요청 한 번에 보내요. 정답 라벨은 앱에서 채점하며 API 이용료가 발생할 수 있어요.")
    if st.button(f"{category} · {count}문장 검증", type="primary"):
        try:
            key = st.secrets.get("OPENAI_API_KEY", "")
        except FileNotFoundError:
            key = ""
        if not key:
            st.warning("Streamlit Secrets의 OPENAI_API_KEY를 확인해 주세요.")
        else:
            try:
                reference_vectors()
                samples = examples[len(results):len(results) + count]
                with st.spinner(f"GPT-5에 {count}문장을 한 번에 보내 검증하는 중…"):
                    predictions = measure_batch(samples, key)
                batch_results = [
                    {"원문": result["원문"], "정답": result["정답"], "GPT": result["예측"],
                     "GPT 시간(초)": result["응답 시간(초)"], "응답 모델": result["모델"],
                     "유형": sample["category"], "상황 번호": sample["scenario_id"],
                     **measure_similarity(sample["sentence"])}
                    for sample, result in zip(samples, predictions, strict=True)
                ]
                results.extend(batch_results)
            except (HTTPError, OSError, ValueError, KeyError) as error:
                st.error(f"검증이 중단됐어요 ({getattr(error, 'code', type(error).__name__)}). 남은 문장부터 이어갈 수 있어요.")
            else:
                st.rerun()

st.subheader("정확도와 문장당 평균 처리 시간")
if not results:
    st.info("첫 검증을 실행하면 두 방식의 실측 결과가 표시돼요.")
    st.stop()
reference_vectors()
for row in results:
    if "유사도 시간(초)" not in row:
        row.update(measure_similarity(row["원문"]))
table = pd.DataFrame(results)
summary = pd.DataFrame([
    {"방식": SIMILARITY, **average_similarity(table)},
    {"방식": GPT, **metrics(table, "GPT")},
])
st.caption(f"두 방식이 모두 처리한 {len(table)}문장 기준 · 응답 모델 {results[-1]['응답 모델']}")
st.caption("유사도는 기준 벡터 준비가 끝난 뒤 문장 하나를 벡터화하고 네 임계값에서 판정하는 전체 시간을 재요. GPT-5의 값은 200문장 묶음의 API 왕복 시간을 문장 수로 나눈 일괄 처리 기준 시간이에요.")
def completed_points(frame):
    points = []
    for end in range(BATCH_SIZE, len(frame) + 1, BATCH_SIZE):
        batch = frame.iloc[end - BATCH_SIZE:end]
        points.extend([
            {"완료 문장 수": end, "분야": batch["유형"].iloc[0], "방식": SIMILARITY, **average_similarity(batch)},
            {"완료 문장 수": end, "분야": batch["유형"].iloc[0], "방식": GPT, **metrics(batch, "GPT")},
        ])
    return points


points = completed_points(table)
st.caption("각 점은 해당 분야 200문장의 결과예요. 예를 들어 X축 400의 점은 201~400번 마케팅 동의 문장을 집계한 값이에요.")
if points:
    chart_data = pd.DataFrame(points)
    chart_data["범례"] = chart_data["방식"].map({SIMILARITY: "유사도", GPT: "GPT-5"})
    a, b = st.columns(2)
    for column, metric, title, scale in [
        (a, "정확도", "정확도 (%)", alt.Scale(domain=[0, 100])),
        (b, "문장당 시간(초)", "문장당 평균 처리 시간 (초)", alt.Scale(zero=True)),
    ]:
        column.markdown(f"**{title}**")
        chart = alt.Chart(chart_data).mark_line(point=alt.OverlayMarkDef(filled=True, size=75)).encode(
            x=alt.X("완료 문장 수:Q", title=None,
                    axis=alt.Axis(values=list(range(BATCH_SIZE, len(examples) + 1, BATCH_SIZE)),
                                  format="d", labelAngle=-45, labelPadding=5, labelOverlap=True),
                    scale=alt.Scale(domain=[BATCH_SIZE, len(examples)], nice=False)),
            y=alt.Y(f"{metric}:Q", title=None, scale=scale),
            color=alt.Color("범례:N", title=None,
                            legend=alt.Legend(orient="top", direction="horizontal", labelLimit=100, offset=10),
                            scale=alt.Scale(domain=["유사도", "GPT-5"], range=["#235aa6", "#aa4d14"])),
            tooltip=["완료 문장 수:Q", "분야:N", "방식:N", alt.Tooltip(f"{metric}:Q", title=title, format=".4f")],
        ).properties(height=270, padding={"left": 16, "top": 12, "right": 20, "bottom": 16})
        column.altair_chart(chart, use_container_width=True)
        column.caption("X축 · 완료 문장 수")

else:
    st.info("첫 200문장의 검증이 끝나면 그래프에 두 방식의 첫 점이 표시돼요.")
st.caption("전체 검증 완료 문장 기준 누적 집계")
st.dataframe(summary, hide_index=True)
with st.expander("임계값별 정확도 · 오탐 · 미탐 · 유보"):
    st.dataframe(pd.DataFrame([
        {"임계값": f"{percent}%", **metrics(table, f"유사도 {percent}%")} for percent in THRESHOLDS
    ]).drop(columns="문장당 시간(초)"), hide_index=True)
st.caption("유사도의 오탐·미탐·유보도 네 조건의 평균 건수예요. 판단 유보는 정확도에서 오답으로 집계해요. 위험 문장을 유보하면 미탐에도 포함해요.")
complete_batches = len(table) // BATCH_SIZE
if complete_batches:
    st.subheader("200문장 묶음별 상세 결과")
    batch_number = st.selectbox(
        "검증 묶음",
        range(1, complete_batches + 1),
        index=complete_batches - 1,
        format_func=lambda n: f"{n}차 · {(n - 1) * BATCH_SIZE + 1}~{n * BATCH_SIZE}번",
        key=f"pilot_detail_batch_{complete_batches}",
    )
    start = (batch_number - 1) * BATCH_SIZE
    batch = table.iloc[start:start + BATCH_SIZE].copy()
    batch.insert(0, "문장 번호", range(start + 1, start + len(batch) + 1))
    st.markdown("**유형별 결과**")
    st.dataframe(pd.DataFrame([
        {"유형": category, "검증 문장": len(group), "방식": label, **result}
        for category, group in batch.groupby("유형", sort=False)
        for label, result in [(SIMILARITY, average_similarity(group)), (GPT, metrics(group, "GPT"))]
    ]), hide_index=True)
    st.markdown("**문장별 판단과 오탐·미탐**")
    percent = st.selectbox("문장별 유사도 판정을 볼 임계값", THRESHOLDS, format_func=lambda value: f"{value}%")
    prediction_column = f"유사도 {percent}%"
    for label, prediction in [("유사도", prediction_column), ("GPT", "GPT")]:
        batch[f"{label} 오류"] = [
            "오탐" if actual == "안전" and predicted == "위험"
            else "미탐 · 판단 유보" if actual == "위험" and predicted == "판단 유보"
            else "미탐" if actual == "위험" and predicted == "안전"
            else "판단 유보" if predicted == "판단 유보"
            else "—"
            for actual, predicted in zip(batch["정답"], batch[prediction], strict=True)
        ]
    columns = ["문장 번호", "유형", "원문", "정답", prediction_column, "유사도 오류", "GPT", "GPT 오류"]
    different, same, errors = st.tabs(["다르게 판단", "같게 판단", "오탐·미탐·유보"])
    with different:
        st.dataframe(batch.loc[batch[prediction_column] != batch["GPT"], columns], hide_index=True)
    with same:
        st.dataframe(batch.loc[batch[prediction_column] == batch["GPT"], columns], hide_index=True)
    with errors:
        st.dataframe(batch.loc[(batch["정답"] != batch[prediction_column]) | (batch["정답"] != batch["GPT"]), columns], hide_index=True)
else:
    st.info("200문장 검증을 마치면 해당 묶음의 유형별 결과와 오탐·미탐 사례를 볼 수 있어요.")

st.download_button("전체 문장별 결과 CSV 저장", table.to_csv(index=False).encode("utf-8-sig"), "pilot-results.csv", mime="text/csv")
