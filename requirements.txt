import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------

# 페이지 설정

# --------------------------------------------------

st.set_page_config(
page_title="영화 데이터 그래프 도감 1 - 시간",
page_icon="🎬",
layout="wide"
)

# --------------------------------------------------

# 제목

# --------------------------------------------------

st.title("🎬 영화 데이터 그래프 도감 1 - 시간")
st.write("1년 동안의 일별 박스오피스 데이터를 시간의 흐름에 따라 살펴봅니다.")

# --------------------------------------------------

# 데이터 불러오기

# --------------------------------------------------

DATA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_daily.csv"

@st.cache_data
def load_data():
df = pd.read_csv(DATA_URL)

```
# 날짜를 실제 날짜(datetime) 형식으로 변환
df["날짜"] = pd.to_datetime(df["날짜"].astype(str), format="%Y%m%d")

# 숫자형 데이터 변환
numeric_columns = ["순위", "일관객", "누적관객", "스크린수", "상영횟수"]

for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

return df
```

try:
df = load_data()

except Exception as e:
st.error("데이터를 불러오는 중 오류가 발생했습니다.")
st.exception(e)
st.stop()

# --------------------------------------------------

# 데이터 소개 구역

# --------------------------------------------------

st.divider()

st.header("📋 데이터 살펴보기")

st.write(f"전체 데이터는 **{len(df):,}개**의 박스오피스 기록으로 이루어져 있습니다.")

with st.expander("데이터 미리 보기"):
st.dataframe(df.head(20), use_container_width=True)

# ==================================================

# 그래프 1. 영화별 날짜에 따른 일관객 변화

# ==================================================

st.divider()

st.header("📈 그래프 1. 시간에 따른 영화별 일관객 변화")

st.write("드롭다운에서 영화를 선택하면 날짜별 일관객 변화를 확인할 수 있습니다.")

# 영화 목록 만들기

movie_list = sorted(df["영화명"].dropna().unique())

selected_movie = st.selectbox(
"🎥 보고 싶은 영화를 선택하세요",
movie_list
)

# 선택한 영화 데이터

movie_df = df[df["영화명"] == selected_movie].copy()

# 날짜 순서대로 정렬

movie_df = movie_df.sort_values("날짜")

# Plotly 선 그래프

fig = px.line(
movie_df,
x="날짜",
y="일관객",
markers=True,
title=f"🎬 {selected_movie}의 날짜별 일관객 변화",
labels={
"날짜": "날짜",
"일관객": "일관객 수"
},
hover_data={
"날짜": "|%Y-%m-%d",
"일관객": ":,"
}
)

fig.update_traces(
hovertemplate="<b>날짜</b>: %{x|%Y-%m-%d}<br>"
"<b>관객수</b>: %{y:,}명"
"<extra></extra>"
)

fig.update_layout(
hovermode="x unified",
xaxis_title="날짜",
yaxis_title="일관객 수(명)"
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------

# 이 그래프로 알 수 있는 것

# --------------------------------------------------

st.info(
"💡 이 그래프로 알 수 있는 것: "
"선택한 영화의 일별 관객 수가 시간에 따라 어떻게 증가하거나 감소했는지 확인할 수 있습니다."
)

# ==================================================

# 그래프 2. 앞으로 추가할 그래프 구역

# ==================================================

st.divider()

st.header("📊 그래프 2. 다음 그래프")

st.write("이곳에는 앞으로 새로운 시간 관련 그래프를 추가할 수 있습니다.")

st.info(
"💡 이 그래프로 알 수 있는 것: "
"앞으로 그래프를 추가한 뒤 이곳에 그래프에서 발견할 수 있는 내용을 한 문장으로 작성합니다."
)

# ==================================================

# 그래프 3. 앞으로 추가할 그래프 구역

# ==================================================

st.divider()

st.header("📊 그래프 3. 다음 그래프")

st.write("이곳에도 새로운 그래프를 추가할 수 있습니다.")

st.info(
"💡 이 그래프로 알 수 있는 것: "
"그래프를 보고 알 수 있는 내용을 한 문장으로 정리합니다."
)

# --------------------------------------------------

# 데이터 정보

# --------------------------------------------------

st.divider()

st.caption(
"데이터: KOBIS 일별 박스오피스 10위권 기록 · "
"그래프 도감은 앞으로 계속 확장할 수 있습니다."
)
