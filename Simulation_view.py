import streamlit as st
import pymysql
import json
import re
import pandas as pd

# ======================
# LaTeX / 텍스트 정리
# ======================
def clean_inline_latex(text):
    text = re.sub(r"\\text\{(.*?)\}", r"\1", text)
    text = re.sub(r"\\frac\{(.*?)\}\{(.*?)\}", r"\1/\2", text)
    text = re.sub(r"\\sqrt\{(.*?)\}", r"√\1", text)
    text = re.sub(r"\\rightarrow|\\to", "→", text)
    text = re.sub(r"\\times", "×", text)
    text = re.sub(r"\\div", "÷", text)
    text = re.sub(r"\\pm", "±", text)
    text = re.sub(r"\\leq", "≤", text)
    text = re.sub(r"\\geq", "≥", text)
    text = re.sub(r"\\neq", "≠", text)
    text = re.sub(r"\\approx", "≈", text)
    text = re.sub(r"\\infty", "∞", text)
    text = re.sub(r"\\", "", text)
    return text

# ======================
# DB 연결
# ======================
def connect_to_db():
    return pymysql.connect(
        host=st.secrets["DB_HOST"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_DATABASE"],
        charset="utf8mb4"
    )

# ======================
# 조회용 함수들
# ======================
def fetch_numbers():
    db = connect_to_db()
    cur = db.cursor()
    cur.execute("SELECT DISTINCT number FROM qna_unique ORDER BY number")
    rows = cur.fetchall()
    cur.close(); db.close()
    return [r[0] for r in rows]

def fetch_names(number):
    db = connect_to_db()
    cur = db.cursor()
    cur.execute(
        "SELECT DISTINCT name FROM qna_unique WHERE number = %s ORDER BY name",
        (number,)
    )
    rows = cur.fetchall()
    cur.close(); db.close()
    return [r[0] for r in rows]

def fetch_topics(number, name):
    db = connect_to_db()
    cur = db.cursor()
    cur.execute(
        """
        SELECT DISTINCT topic
        FROM qna_unique
        WHERE number = %s AND name = %s
        ORDER BY topic
        """,
        (number, name)
    )
    rows = cur.fetchall()
    cur.close(); db.close()
    return [r[0] for r in rows]

def fetch_chat(number, name, topic):
    db = connect_to_db()
    cur = db.cursor()
    cur.execute(
        """
        SELECT chat
        FROM qna_unique
        WHERE number = %s AND name = %s AND topic = %s
        """,
        (number, name, topic)
    )
    row = cur.fetchone()
    cur.close(); db.close()
    return row[0] if row else None

def delete_chat(number, name, topic):
    db = connect_to_db()
    cur = db.cursor()
    cur.execute(
        """
        DELETE FROM qna_unique
        WHERE number = %s AND name = %s AND topic = %s
        """,
        (number, name, topic)
    )
    db.commit()
    cur.close(); db.close()

# ======================
# 기본 UI
# ======================
st.title("학생 AI 대화 이력 조회(개발자용)")

password = st.text_input("관리자 비밀번호", type="password")
if password != st.secrets["PASSWORD"]:
    st.stop()

# ======================
# 학번 → 이름 → 토픽 선택
# ======================
numbers = fetch_numbers()
number = st.selectbox("학번 선택", ["선택하세요"] + numbers)
if number == "선택하세요":
    st.stop()

names = fetch_names(number)
name = st.selectbox("이름 선택", ["선택하세요"] + names)
if name == "선택하세요":
    st.stop()

topics = fetch_topics(number, name)
topic = st.selectbox("토픽 선택", ["선택하세요"] + topics)
if topic == "선택하세요":
    st.stop()

# ======================
# 대화 불러오기
# ======================
chat_raw = fetch_chat(number, name, topic)
if not chat_raw:
    st.warning("대화 기록이 없습니다.")
    st.stop()

try:
    chat = json.loads(chat_raw)
except json.JSONDecodeError:
    st.error("대화 데이터 JSON 오류")
    st.stop()

st.subheader("대화 내용")

chat_table = []

for msg in chat:
    role = "학생" if msg["role"] == "user" else "AI"
    content = msg["content"]

    parts = re.split(r"(\+{5}.*?\+{5})", content, flags=re.DOTALL)
    cleaned = []

    for part in parts:
        if part.startswith("+++++") and part.endswith("+++++"):
            code = part[5:-5].strip()
            st.code(code, language="javascript")
            cleaned.append(code)
        else:
            text = clean_inline_latex(part.strip())
            if text:
                st.write(f"**{role}:** {text}")
                cleaned.append(text)

    chat_table.append({
        "말한 사람": name if role == "학생" else "AI",
        "내용": " ".join(cleaned),
        "토픽": topic
    })

# ======================
# DF 형태 출력 (첨부파일 동일)
# ======================
st.subheader("복사용 표")
df = pd.DataFrame(chat_table)
st.markdown(df.to_html(index=False), unsafe_allow_html=True)

# ======================
# 삭제 기능
# ======================
if "delete_confirm" not in st.session_state:
    st.session_state.delete_confirm = False

area = st.empty()

if not st.session_state.delete_confirm:
    if area.button("❌ 이 대화 전체 삭제"):
        st.session_state.delete_confirm = True
        st.rerun()
else:
    st.warning("정말 삭제하시겠습니까?")
    if area.button("✅ 삭제 확정"):
        delete_chat(number, name, topic)
        st.success("삭제 완료")
        st.session_state.delete_confirm = False