import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# --------------------------------------------------
# 페이지 기본 설정
# --------------------------------------------------
st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 어제의 박스오피스")
st.caption("KOBIS 영화관입장권 통합전산망 일별 박스오피스 기준")

# --------------------------------------------------
# 한국 시간 기준으로 '어제' 날짜 계산하기
# 배포 서버가 해외에 있어도 Asia/Seoul 시간을 사용합니다.
# --------------------------------------------------
KST = ZoneInfo("Asia/Seoul")

today_kst = datetime.now(KST).date()
yesterday = today_kst - timedelta(days=1)

# KOBIS API가 요구하는 yyyymmdd 형식
target_date = yesterday.strftime("%Y%m%d")

# 화면에 보여 줄 날짜 형식
display_date = yesterday.strftime("%Y년 %m월 %d일")

st.subheader(f"📅 {display_date} 박스오피스")


# --------------------------------------------------
# 숫자 문자열을 안전하게 숫자로 바꾸는 함수
# API에서 "12345"처럼 문자열로 전달되는 값을 숫자로 변환합니다.
# --------------------------------------------------
def to_number(value):
    try:
        return int(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return 0


# --------------------------------------------------
# API 호출 함수
# 같은 날짜의 데이터는 1시간 동안 캐시에 저장합니다.
# 따라서 페이지를 다시 실행해도 불필요한 API 호출을 줄일 수 있습니다.
# --------------------------------------------------
@st.cache_data(ttl=3600)
def get_boxoffice_data(date_string):
    """
    KOBIS 일별 박스오피스 데이터를 가져오는 함수

    date_string: yyyymmdd 형식의 날짜
    """

    # Streamlit secrets에서 인증키를 가져옵니다.
    # 코드 안에는 인증키를 직접 작성하지 않습니다.
    api_key = st.secrets["KOBIS_KEY"]

    url = (
        "https://www.kobis.or.kr/"
        "kobisopenapi/webservice/rest/boxoffice/"
        "searchDailyBoxOfficeList.json"
    )

    params = {
        "key": api_key,
        "targetDt": date_string
    }

    # API 요청
    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    # HTTP 오류가 있으면 예외 발생
    response.raise_for_status()

    # JSON 데이터로 변환
    return response.json()


# --------------------------------------------------
# 오류 안내를 보여 주는 함수
# --------------------------------------------------
def show_help_message(error_type, detail=""):

    if error_type == "secret":
        st.error("🔑 인증키 설정을 확인해 주세요.")
        st.info(
            "Streamlit Cloud의 Secrets 설정에 "
            "`KOBIS_KEY`가 올바르게 등록되어 있는지 확인하세요.\n\n"
            "예시:\n"
            "```toml\n"
            'KOBIS_KEY = "발급받은_인증키"\n'
            "```"
        )

    elif error_type == "fault":
        st.error("⚠️ KOBIS API에서 오류 정보를 반환했습니다.")
        st.info(
            "다음 항목을 확인해 주세요.\n\n"
            "1. KOBIS 인증키가 올바른지\n"
            "2. 인증키가 정상적으로 발급되었는지\n"
            "3. API 사용 권한이나 일일 요청 제한에 문제가 없는지"
        )

        if detail:
            st.warning(f"API 오류 내용: {detail}")

    elif error_type == "empty":
        st.warning("📭 조회된 박스오피스 영화가 없습니다.")
        st.info(
            "다음 사항을 확인해 주세요.\n\n"
            "1. 조회 날짜가 올바른지\n"
            "2. 해당 날짜의 박스오피스 집계가 완료되었는지\n"
            "3. KOBIS API가 정상적으로 데이터를 제공하고 있는지"
        )

    elif error_type == "request":
        st.error("🌐 KOBIS API 요청에 실패했습니다.")
        st.info(
            "다음 사항을 확인해 주세요.\n\n"
            "1. 인터넷 연결 상태\n"
            "2. KOBIS API 서버 상태\n"
            "3. Streamlit Cloud의 네트워크 환경\n"
            "4. 잠시 후 다시 접속해 보기"
        )

        if detail:
            st.caption(f"오류 정보: {detail}")


# --------------------------------------------------
# 데이터 가져오기
# --------------------------------------------------
try:
    data = get_boxoffice_data(target_date)

except KeyError:
    # secrets에 KOBIS_KEY가 없는 경우
    show_help_message("secret")
    st.stop()

except requests.exceptions.RequestException as e:
    # 인터넷 연결, 서버 오류, 시간 초과 등의 경우
    show_help_message("request", str(e))
    st.stop()

except Exception as e:
    # 그 밖의 예상하지 못한 오류
    st.error("⚠️ 데이터를 처리하는 중 문제가 발생했습니다.")
    st.caption(f"오류 정보: {e}")
    st.stop()


# --------------------------------------------------
# API 응답에 faultInfo가 있는지 확인
# KOBIS는 인증키 오류가 있어도 HTTP 상태코드 200을
# 반환할 수 있으므로 반드시 JSON 내부도 확인해야 합니다.
# --------------------------------------------------
if "faultInfo" in data:
    fault_info = data["faultInfo"]

    # faultInfo가 문자열일 수도 있고 객체일 수도 있으므로 처리
    if isinstance(fault_info, dict):
        detail = (
            fault_info.get("message")
            or fault_info.get("faultString")
            or str(fault_info)
        )
    else:
        detail = str(fault_info)

    show_help_message("fault", detail)
    st.stop()


# --------------------------------------------------
# boxOfficeResult와 영화 목록 가져오기
# --------------------------------------------------
boxoffice_result = data.get("boxOfficeResult", {})
movie_list = boxoffice_result.get("dailyBoxOfficeList", [])

# 영화 목록이 비어 있는 경우
if not movie_list:
    show_help_message("empty")
    st.stop()


# --------------------------------------------------
# 필요한 데이터만 골라서 표 형태로 만들기
# 숫자 문자열은 int로 변환합니다.
# --------------------------------------------------
rows = []

for movie in movie_list:
    rows.append({
        "순위": to_number(movie.get("rank")),
        "영화명": movie.get("movieNm", ""),
        "개봉일": movie.get("openDt", ""),
        "관객수": to_number(movie.get("audiCnt")),
        "누적관객": to_number(movie.get("audiAcc")),
        "스크린수": to_number(movie.get("scrnCnt"))
    })

df = pd.DataFrame(rows)

# 순위를 숫자로 정렬
df = df.sort_values("순위").reset_index(drop=True)


# --------------------------------------------------
# 1위 영화 정보 카드
# --------------------------------------------------
if not df.empty:

    first_movie = df.iloc[0]

    st.divider()
    st.subheader(f"🏆 오늘의 1위: {first_movie['영화명']}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="🎟️ 어제 관객수",
            value=f"{first_movie['관객수']:,}명"
        )

    with col2:
        st.metric(
            label="👥 누적 관객수",
            value=f"{first_movie['누적관객']:,}명"
        )

    with col3:
        st.metric(
            label="🎬 스크린수",
            value=f"{first_movie['스크린수']:,}개"
        )


# --------------------------------------------------
# 관객수 상위 5편 막대그래프
# --------------------------------------------------
st.divider()
st.subheader("📊 관객수 상위 5편")

top5 = (
    df.sort_values("관객수", ascending=False)
      .head(5)
      .set_index("영화명")
)

st.bar_chart(top5["관객수"])


# --------------------------------------------------
# 전체 박스오피스 표
# --------------------------------------------------
st.divider()
st.subheader("📋 전체 박스오피스")

# 화면에 숫자를 보기 좋게 표시하기 위해 복사본 생성
display_df = df.copy()

display_df["관객수"] = display_df["관객수"].map(
    lambda x: f"{x:,}"
)

display_df["누적관객"] = display_df["누적관객"].map(
    lambda x: f"{x:,}"
)

display_df["스크린수"] = display_df["스크린수"].map(
    lambda x: f"{x:,}"
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# 데이터 출처와 조회 정보
# --------------------------------------------------
st.divider()
st.caption(
    f"조회 날짜: {target_date} (한국 시간 기준 어제) | "
    "출처: KOBIS 영화관입장권 통합전산망"
)
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# --------------------------------------------------
# 페이지 기본 설정
# --------------------------------------------------
st.set_page_config(
    page_title="일별 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 일별 박스오피스")
st.caption("KOBIS 영화관입장권 통합전산망 일별 박스오피스")


# --------------------------------------------------
# 한국 시간(KST) 설정
# 배포 서버가 해외에 있어도 한국 시간을 기준으로 합니다.
# --------------------------------------------------
KST = ZoneInfo("Asia/Seoul")

# 한국 시간 기준 오늘과 어제 계산
today_kst = datetime.now(KST).date()
yesterday = today_kst - timedelta(days=1)


# --------------------------------------------------
# 날짜 선택
# 오늘은 아직 집계되지 않았으므로 가장 늦게 선택할 수 있는
# 날짜를 '어제'로 제한합니다.
# --------------------------------------------------
selected_date = st.date_input(
    "📅 조회할 날짜를 선택하세요",
    value=yesterday,
    max_value=yesterday
)

# KOBIS API가 요구하는 yyyymmdd 형식으로 변환
target_date = selected_date.strftime("%Y%m%d")

st.subheader(
    f"📅 {selected_date.strftime('%Y년 %m월 %d일')} 박스오피스"
)


# --------------------------------------------------
# 숫자 문자열을 안전하게 숫자로 바꾸는 함수
# KOBIS API의 숫자 데이터는 문자열로 전달됩니다.
# 예: "12345" → 12345
# --------------------------------------------------
def to_number(value):
    try:
        return int(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return 0


# --------------------------------------------------
# 순위 변동을 보기 좋게 표시하는 함수
#
# rankInten:
# 양수 → 순위 상승 🔺
# 음수 → 순위 하락 🔻
# 0 → 순위 변동 없음 -
# --------------------------------------------------
def format_rank_change(value):
    number = to_number(value)

    if number > 0:
        # 순위가 오른 영화
        return f"🔺 {number}"

    elif number < 0:
        # 순위가 내린 영화
        return f"🔻 {abs(number)}"

    else:
        # 순위 변동 없음
        return "-"


# --------------------------------------------------
# KOBIS API에서 데이터를 가져오는 함수
#
# 같은 날짜를 다시 조회하면 1시간 동안 저장된 결과를 사용합니다.
# --------------------------------------------------
@st.cache_data(ttl=3600)
def get_boxoffice_data(date_string):
    """
    선택한 날짜의 KOBIS 일별 박스오피스 데이터를 가져옵니다.
    """

    # Streamlit Secrets에서 API 인증키 가져오기
    # 코드 안에는 인증키를 직접 작성하지 않습니다.
    api_key = st.secrets["KOBIS_KEY"]

    # KOBIS 일별 박스오피스 API 주소
    url = (
        "https://www.kobis.or.kr/"
        "kobisopenapi/webservice/rest/boxoffice/"
        "searchDailyBoxOfficeList.json"
    )

    # API 요청에 필요한 값
    params = {
        "key": api_key,
        "targetDt": date_string
    }

    # API 요청
    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    # HTTP 오류가 발생하면 예외 처리
    response.raise_for_status()

    # 응답을 JSON 형태로 반환
    return response.json()


# --------------------------------------------------
# 오류 안내 함수
# --------------------------------------------------
def show_help_message(error_type, detail=""):

    # Secrets에 인증키가 없는 경우
    if error_type == "secret":
        st.error("🔑 KOBIS 인증키 설정을 확인해 주세요.")

        st.info(
            "Streamlit Cloud의 Secrets에 "
            "`KOBIS_KEY`가 올바르게 등록되어 있는지 확인하세요.\n\n"
            "예시:\n"
            "```toml\n"
            'KOBIS_KEY = "발급받은_인증키"\n'
            "```"
        )

    # KOBIS API가 faultInfo를 반환한 경우
    elif error_type == "fault":
        st.error("⚠️ KOBIS API에서 오류 정보를 반환했습니다.")

        st.info(
            "다음 사항을 확인해 주세요.\n\n"
            "1. KOBIS 인증키가 올바른지\n"
            "2. 인증키가 정상적으로 발급되었는지\n"
            "3. API 사용 권한에 문제가 없는지\n"
            "4. API 요청 제한을 초과하지 않았는지"
        )

        if detail:
            st.warning(f"API 오류 내용: {detail}")

    # 네트워크 또는 서버 요청 실패
    elif error_type == "request":
        st.error("🌐 KOBIS API 요청에 실패했습니다.")

        st.info(
            "다음 사항을 확인해 주세요.\n\n"
            "1. 인터넷 연결 상태\n"
            "2. KOBIS API 서버 상태\n"
            "3. Streamlit Cloud의 네트워크 환경\n"
            "4. 잠시 후 다시 접속해 보기"
        )

        if detail:
            st.caption(f"오류 정보: {detail}")


# --------------------------------------------------
# API 데이터 가져오기
# --------------------------------------------------
try:
    data = get_boxoffice_data(target_date)

except KeyError:
    # secrets에 KOBIS_KEY가 없는 경우
    show_help_message("secret")
    st.stop()

except requests.exceptions.RequestException as e:
    # 네트워크, 서버, 시간 초과 등의 오류
    show_help_message("request", str(e))
    st.stop()

except Exception as e:
    # 예상하지 못한 오류
    st.error("⚠️ 데이터를 처리하는 중 문제가 발생했습니다.")
    st.caption(f"오류 정보: {e}")
    st.stop()


# --------------------------------------------------
# KOBIS API의 faultInfo 확인
#
# 인증키 오류가 있어도 HTTP 상태코드가 200으로 올 수 있으므로
# JSON 안의 faultInfo를 반드시 확인합니다.
# --------------------------------------------------
if "faultInfo" in data:

    fault_info = data["faultInfo"]

    # faultInfo가 딕셔너리인 경우
    if isinstance(fault_info, dict):
        detail = (
            fault_info.get("message")
            or fault_info.get("faultString")
            or str(fault_info)
        )

    # 문자열 등 다른 형태인 경우
    else:
        detail = str(fault_info)

    show_help_message("fault", detail)
    st.stop()


# --------------------------------------------------
# boxOfficeResult 안에서 영화 목록 가져오기
# --------------------------------------------------
boxoffice_result = data.get("boxOfficeResult", {})
movie_list = boxoffice_result.get("dailyBoxOfficeList", [])


# --------------------------------------------------
# 선택한 날짜의 영화 목록이 없는 경우
# --------------------------------------------------
if not movie_list:

    st.warning("⏳ 그날은 아직 집계 전입니다.")

    st.info(
        "KOBIS의 일별 박스오피스 데이터가 아직 제공되지 않았습니다.\n\n"
        "잠시 후 다시 확인하거나 다른 날짜를 선택해 주세요."
    )

    st.stop()


# --------------------------------------------------
# API 데이터를 표에 사용할 형태로 변환
# --------------------------------------------------
rows = []

for movie in movie_list:

    # 숫자 데이터는 문자열로 오므로 숫자로 변환
    rank = to_number(movie.get("rank"))
    rank_inten = to_number(movie.get("rankInten"))
    audi_cnt = to_number(movie.get("audiCnt"))
    audi_acc = to_number(movie.get("audiAcc"))
    scrn_cnt = to_number(movie.get("scrnCnt"))

    # 영화 이름 가져오기
    movie_name = movie.get("movieNm", "")

    # ------------------------------------------------
    # 누적 관객수가 100만 명 이상이면 트로피 표시
    # ------------------------------------------------
    if audi_acc >= 1_000_000:
        movie_name = f"{movie_name} 🏆"

    rows.append({
        "순위": rank,
        "전날 대비": format_rank_change(rank_inten),
        "영화명": movie_name,
        "개봉일": movie.get("openDt", ""),
        "관객수": audi_cnt,
        "누적관객": audi_acc,
        "스크린수": scrn_cnt
    })


# 데이터프레임 만들기
df = pd.DataFrame(rows)

# 순위를 숫자로 정렬
df = df.sort_values("순위").reset_index(drop=True)


# --------------------------------------------------
# 1위 영화 정보
# --------------------------------------------------
if not df.empty:

    first_movie = df.iloc[0]

    st.divider()

    st.subheader(
        f"🏆 1위 영화: {first_movie['영화명']}"
    )

    # 지표 카드 3개
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="🎟️ 그날 관객수",
            value=f"{first_movie['관객수']:,}명"
        )

    with col2:
        st.metric(
            label="👥 누적 관객수",
            value=f"{first_movie['누적관객']:,}명"
        )

    with col3:
        st.metric(
            label="🎬 스크린수",
            value=f"{first_movie['스크린수']:,}개"
        )


# --------------------------------------------------
# 관객수 상위 5편 막대그래프
# --------------------------------------------------
st.divider()
st.subheader("📊 관객수 상위 5편")

# 관객수를 기준으로 내림차순 정렬 후 상위 5편 선택
top5 = (
    df.sort_values("관객수", ascending=False)
      .head(5)
      .set_index("영화명")
)

st.bar_chart(top5["관객수"])


# --------------------------------------------------
# 전체 박스오피스 표
# --------------------------------------------------
st.divider()
st.subheader("📋 전체 박스오피스")

# 원본 숫자 데이터는 그래프와 정렬에 사용하기 위해 유지하고,
# 화면 표시용 복사본을 따로 만듭니다.
display_df = df.copy()

# 숫자를 보기 좋게 쉼표와 함께 표시
display_df["관객수"] = display_df["관객수"].map(
    lambda x: f"{x:,}"
)

display_df["누적관객"] = display_df["누적관객"].map(
    lambda x: f"{x:,}"
)

display_df["스크린수"] = display_df["스크린수"].map(
    lambda x: f"{x:,}"
)


# 표 표시
st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# 페이지 아래쪽 정보
# --------------------------------------------------
st.divider()

st.caption(
    f"조회 날짜: {selected_date.strftime('%Y년 %m월 %d일')} | "
    "한국 시간(KST) 기준 | "
    "출처: KOBIS 영화관입장권 통합전산망"
)
````
