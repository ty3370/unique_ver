import streamlit as st
import pymysql
import json
import re
import pandas as pd

# 조회에서 제외할 토픽들
EXCLUDED_TOPICS = (
    "Ⅰ. 화학 반응의 규칙과 에너지 변화",
    "Ⅱ. 기권과 날씨",
    "Ⅲ. 운동과 에너지",
)

def clean_inline_latex(text):
    text = re.sub(r",\s*\\text\{(.*?)\}", r" \1", text)
    text = re.sub(r"\\text\{(.*?)\}", r"\1", text)
    text = re.sub(r"\\ce\{(.*?)\}", r"\1", text)
    text = re.sub(r"\\frac\{(.*?)\}\{(.*?)\}", r"\1/\2", text)
    text = re.sub(r"\\sqrt\{(.*?)\}", r"√\1", text)
    text = re.sub(r"\\rightarrow|\\to", "→", text)
    text = re.sub(r"\^\{(.*?)\}", r"^\1", text)
    text = re.sub(r"_\{(.*?)\}", r"_\1", text)
    text = re.sub(r"\^([0-9])", r"^\1", text)
    text = re.sub(r"_([0-9])", r"\1", text)
    text = re.sub(r"\\", "", text)

    replacements = {
        r"\\perp": "⟂",
        r"\\angle": "∠",
        r"\\parallel": "∥",
        r"\\infty": "∞",
        r"\\approx": "≈",
        r"\\neq": "≠",
        r"\\leq": "≤",
        r"\\geq": "≥",
        r"\\pm": "±",
    }
    for p, s in replacements.items():
        text = re.sub(p, s, text)

    return text.strip()

def connect_to_db():
    return pymysql.connect(
        host=st.secrets["DB_HOST"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_DATABASE"],
        charset="utf8mb4"
    )

@st.cache_data(show_spinner=False)
def fetch_all_rows():
    db = connect_to_db()
    # 필요한 컬럼만 가져오면 더 빠르고 메모리도 절약됨
    df = pd.read_sql(
        """
        SELECT number, name, code, topic, chat
        FROM qna_unique
        """,
        db
    )
    db.close()
    return df

def delete_chat(number, name, topic):
    db = connect_to_db()
    cur = db.cursor()
    cur.execute(
        "DELETE FROM qna_unique WHERE number=%s AND name=%s AND topic=%s",
        (number, name, topic)
    )
    db.commit()
    cur.close()
    db.close()

st.title("AI 대화 기록 조회")

password = st.text_input("관리자 비밀번호", type="password")
if password != st.secrets["PASSWORD"]:
    st.stop()

df_all = fetch_all_rows()

# 학번
numbers = sorted(df_all["number"].dropna().unique().tolist())
number = st.selectbox("학번", ["선택"] + numbers)
if number == "선택":
    st.stop()

df_n = df_all[df_all["number"] == number]

# 이름
names = sorted(df_n["name"].dropna().unique().tolist())
name = st.selectbox("이름", ["선택"] + names)
if name == "선택":
    st.stop()

df_nn = df_n[df_n["name"] == name]

# 식별코드
codes = sorted(df_nn["code"].dropna().unique().tolist())
code = st.selectbox("식별코드", ["선택"] + codes)
if code == "선택":
    st.stop()

df_nnc = df_nn[df_nn["code"] == code]

topics = sorted(
    df_nnc[~df_nnc["topic"].isin(EXCLUDED_TOPICS)]["topic"].dropna().unique().tolist()
)
topic = st.selectbox("토픽", ["선택"] + topics)
if topic == "선택":
    st.stop()

df_final = df_nnc[df_nnc["topic"] == topic]
chat_raw = None
if not df_final.empty:
    # 동일 키로 여러 row가 있으면 첫 번째 사용 (기존 fetch_chat도 단건 fetch였던 것과 유사)
    chat_raw = df_final.iloc[0]["chat"]

if not chat_raw:
    st.warning("대화 없음")
    st.stop()

try:
    chat = json.loads(chat_raw)
except Exception:
    st.error("대화 데이터 오류")
    st.stop()

st.subheader("대화 내용")

chat_table = []

for msg in chat:
    role = "학생" if msg["role"] == "user" else "AI"
    content = msg["content"]

    parts = re.split(r"(\+{5}.*?\+{5})", content, flags=re.DOTALL)

    df_texts = []

    for part in parts:
        if part.startswith("+++++") and part.endswith("+++++"):
            code_block = part[5:-5].strip()
            st.code(code_block, language="javascript")
        else:
            text = clean_inline_latex(part)
            if text:
                st.write(f"{role}: {text}")
                df_texts.append(text)

    chat_table.append({
        "말한 사람": name if role == "학생" else "AI",
        "내용": " ".join(df_texts),
        "토픽": topic
    })

st.subheader("복사용 표")
df = pd.DataFrame(chat_table)
st.markdown(df.to_html(index=False), unsafe_allow_html=True)

if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = False

area = st.empty()

if not st.session_state.confirm_delete:
    if area.button("삭제"):
        st.session_state.confirm_delete = True
        st.rerun()
else:
    st.warning("정말 삭제하시겠습니까?")
    if area.button("삭제 확정"):
        delete_chat(number, name, topic)
        st.cache_data.clear()
        st.session_state.confirm_delete = False
        st.success("삭제 완료")