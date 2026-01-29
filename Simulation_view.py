import streamlit as st
import pymysql
import json
import re
import pandas as pd

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

def fetch_numbers():
    db = connect_to_db()
    cur = db.cursor()
    cur.execute("SELECT DISTINCT number FROM qna_unique ORDER BY number")
    rows = cur.fetchall()
    cur.close()
    db.close()
    return [r[0] for r in rows]

def fetch_names(number):
    db = connect_to_db()
    cur = db.cursor()
    cur.execute(
        "SELECT DISTINCT name FROM qna_unique WHERE number=%s ORDER BY name",
        (number,)
    )
    rows = cur.fetchall()
    cur.close()
    db.close()
    return [r[0] for r in rows]

def fetch_codes(number, name):
    db = connect_to_db()
    cur = db.cursor()
    cur.execute(
        """
        SELECT DISTINCT code
        FROM qna_unique
        WHERE number=%s AND name=%s
        ORDER BY code
        """,
        (number, name)
    )
    rows = cur.fetchall()
    cur.close()
    db.close()
    return [r[0] for r in rows]

def fetch_topics(number, name, code):
    db = connect_to_db()
    cur = db.cursor()
    cur.execute(
        """
        SELECT DISTINCT topic
        FROM qna_unique
        WHERE number=%s AND name=%s AND code=%s
        ORDER BY topic
        """,
        (number, name, code)
    )
    rows = cur.fetchall()
    cur.close()
    db.close()
    return [r[0] for r in rows]

def fetch_chat(number, name, code, topic):
    db = connect_to_db()
    cur = db.cursor()
    cur.execute(
        """
        SELECT chat
        FROM qna_unique
        WHERE number=%s AND name=%s AND code=%s AND topic=%s
        """,
        (number, name, code, topic)
    )
    row = cur.fetchone()
    cur.close()
    db.close()
    return row[0] if row else None

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

numbers = fetch_numbers()
number = st.selectbox("학번", ["선택"] + numbers)
if number == "선택":
    st.stop()

names = fetch_names(number)
name = st.selectbox("이름", ["선택"] + names)
if name == "선택":
    st.stop()

codes = fetch_codes(number, name)
code = st.selectbox("식별코드", ["선택"] + codes)
if code == "선택":
    st.stop()

topics = fetch_topics(number, name, code)
topic = st.selectbox("토픽", ["선택"] + topics)
if topic == "선택":
    st.stop()

chat_raw = fetch_chat(number, name, code, topic)
if not chat_raw:
    st.warning("대화 없음")
    st.stop()

try:
    chat = json.loads(chat_raw)
except Exception:
    st.error("대화 데이터 오류")
    st.stop()

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
                df_texts.append(text)

    chat_table.append({
        "말한 사람": name if role == "학생" else "AI",
        "내용": " ".join(df_texts)
    })

st.subheader("복사용 표")
df = pd.DataFrame(chat_table)
st.markdown(df.to_html(index=False), unsafe_allow_html=True)

st.subheader("대화 내용")

for msg in chat:
    role = "학생" if msg["role"] == "user" else "AI"
    content = msg["content"]

    parts = re.split(r"(\+{5}.*?\+{5})", content, flags=re.DOTALL)

    for part in parts:
        if part.startswith("+++++") and part.endswith("+++++"):
            code_block = part[5:-5].strip()
            st.code(code_block, language="javascript")
        else:
            text = clean_inline_latex(part)
            if text:
                st.write(f"{role}: {text}")

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
        st.session_state.confirm_delete = False
        st.success("삭제 완료")