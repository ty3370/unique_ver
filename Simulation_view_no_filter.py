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

def fetch_all_records():
    db = connect_to_db()
    cur = db.cursor()
    cur.execute("""
        SELECT number, name, code, topic, chat
        FROM qna_unique
        ORDER BY number, name, code, topic
    """)
    rows = cur.fetchall()
    cur.close()
    db.close()
    return rows

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

records = fetch_all_records()
if not records:
    st.warning("데이터가 없습니다.")
    st.stop()

df_all = pd.DataFrame(
    records,
    columns=["number", "name", "code", "topic", "chat"]
)

numbers = sorted(df_all["number"].unique().tolist())
number = st.selectbox("학번", ["선택"] + numbers)
if number == "선택":
    st.stop()

df_n = df_all[df_all["number"] == number]

names = sorted(df_n["name"].unique().tolist())
name = st.selectbox("이름", ["선택"] + names)
if name == "선택":
    st.stop()

df_nn = df_n[df_n["name"] == name]

codes = sorted(df_nn["code"].unique().tolist())
code = st.selectbox("식별코드", ["선택"] + codes)
if code == "선택":
    st.stop()

df_nnc = df_nn[df_nn["code"] == code]

topics = sorted(df_nnc["topic"].unique().tolist())
topic = st.selectbox("토픽", ["선택"] + topics)
if topic == "선택":
    st.stop()

row = df_nnc[df_nnc["topic"] == topic].iloc[0]
chat_raw = row["chat"]

try:
    chat = json.loads(chat_raw)
except Exception:
    st.error("대화 데이터 오류")
    st.stop()

st.subheader("대화 내용")

chat_table = []
code_counter = 0

for msg in chat:
    role = "학생" if msg["role"] == "user" else "AI"
    content = msg["content"]

    parts = re.split(r"(\+{5}.*?\+{5})", content, flags=re.DOTALL)
    df_texts = []

    for part in parts:
        if part.startswith("+++++") and part.endswith("+++++"):
            code_counter += 1
            st.markdown(f"**💡 시뮬레이션 코드 [Code Version {code_counter}]**")
            st.code(part[5:-5].strip(), language="javascript")
        else:
            text = clean_inline_latex(part)
            if text:
                st.write(f"{role}: {text}")
                df_texts.append(text)

    label = f"[Code Version {code_counter}] " if "+++++" in content else ""
    chat_table.append({
        "말한 사람": name if role == "학생" else "AI",
        "내용": label + " ".join(df_texts),
        "토픽": topic
    })

st.subheader("복사용 표")
df_out = pd.DataFrame(chat_table)
st.markdown(df_out.to_html(index=False), unsafe_allow_html=True)

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