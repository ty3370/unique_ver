import streamlit as st
import pymysql
import json
import re

# 환경 변수
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

import streamlit as st
import pymysql
import json
import re

# ===== LaTeX 텍스트 정리 함수 =====
def clean_inline_latex(text):
    text = re.sub(r",\s*\\text\{(.*?)\}", r" \1", text)
    text = re.sub(r"\\text\{(.*?)\}", r"\1", text)
    text = re.sub(r"\\ce\{(.*?)\}", r"\1", text)
    text = re.sub(r"\\frac\{(.*?)\}\{(.*?)\}", r"\1/\2", text)
    text = re.sub(r"\\sqrt\{(.*?)\}", r"√\1", text)
    text = re.sub(r"\\rightarrow", "→", text)
    text = re.sub(r"\\to", "→", text)
    text = re.sub(r"\^\{(.*?)\}", r"^\1", text)
    text = re.sub(r"_\{(.*?)\}", r"_\1", text)
    text = re.sub(r"\^([0-9])", r"^\1", text)
    text = re.sub(r"_([0-9])", r"\1", text)
    text = re.sub(r"\\", "", text)
    text = re.sub(r"\(\((.*?)\)\)", r"\1", text)
    text = re.sub(r"\(([^()]*\\[a-z]+[^()]*)\)", lambda m: clean_inline_latex(m.group(1)), text)
    text = re.sub(r"\b(times)\b", "×", text)
    text = re.sub(r"\b(div|divided by)\b", "÷", text)
    text = re.sub(r"\b(plus)\b", "+", text)
    text = re.sub(r"\b(minus)\b", "-", text)
    return text

# ===== DB 연결 =====
def connect_to_db():
    return pymysql.connect(
        host=st.secrets["DB_HOST"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_DATABASE"],
        charset='utf8mb4'
    )

# ===== 학생 목록 가져오기 =====
def fetch_students(subject, unit, subunit, topic, subtopic):
    try:
        db = connect_to_db()
        cursor = db.cursor()
        query = """
        SELECT DISTINCT number, name, code
        FROM qna_unique
        WHERE subject=%s AND unit=%s AND subunit=%s AND topic=%s AND subtopic=%s
        ORDER BY number
        """
        cursor.execute(query, (subject, unit, subunit, topic, subtopic))
        students = cursor.fetchall()
        cursor.close()
        db.close()
        return students
    except pymysql.MySQLError as e:
        st.error(f"데이터베이스 오류: {e}")
        return []

# ===== 대화 가져오기 =====
def fetch_chat(number, name, code, subject, unit, subunit, topic, subtopic):
    try:
        db = connect_to_db()
        cursor = db.cursor()
        query = """
        SELECT chat
        FROM qna_unique
        WHERE number=%s AND name=%s AND code=%s
          AND subject=%s AND unit=%s AND subunit=%s AND topic=%s AND subtopic=%s
        """
        cursor.execute(query, (number, name, code, subject, unit, subunit, topic, subtopic))
        result = cursor.fetchone()
        cursor.close()
        db.close()
        return result[0] if result else None
    except pymysql.MySQLError as e:
        st.error(f"데이터베이스 오류: {e}")
        return None

# ===== UI =====
st.title("학생의 인공지능 사용 내역(교사용)")

password = st.text_input("비밀번호를 입력하세요", type="password")

if password == st.secrets["PASSWORD"]:
    subject = st.selectbox("과목을 선택하세요.", ["과목 선택", "과학"])
    if subject == "과목 선택": st.stop()

    units = {"과학": ["대단원 선택", "Ⅳ. 자극과 반응", "Ⅴ. 생식과 유전", "Ⅵ. 에너지 전환과 보존"]}
    unit = st.selectbox("대단원을 선택하세요.", units[subject])
    if unit == "대단원 선택": st.stop()

    subunits_map = {
        "Ⅳ. 자극과 반응": ["중단원 선택", "1. 자극과 감각 기관", "2. 자극의 전달과 반응"],
        "Ⅴ. 생식과 유전": ["중단원 선택", "1. 생장과 생식", "2. 유전"],
        "Ⅵ. 에너지 전환과 보존": ["중단원 선택", "1. 역학적 에너지 전환과 보존", "2. 에너지의 전환과 이용"]
    }
    subunit = st.selectbox("중단원을 선택하세요.", subunits_map[unit])
    if subunit == "중단원 선택": st.stop()

    topics_map = {
        "1. 자극과 감각 기관": ["소단원 선택", "01. 빛을 보는 눈", "02. 소리를 듣고 균형을 잡는 귀"],
        "2. 자극의 전달과 반응": ["소단원 선택", "01. 신경계는 신호를 전달해", "02. 자극에서 반응이 일어나기까지"],
    }
    topic = st.selectbox("소단원을 선택하세요.", topics_map[subunit])
    if topic == "소단원 선택": st.stop()

    # topic 안에서 추가 선택
    subtopics_map = {
        "01. 빛을 보는 눈": ["세부 선택", "문항 1", "문항 2"],
        "02. 소리를 듣고 균형을 잡는 귀": ["세부 선택", "문항 1", "문항 2"]
    }
    subtopic = st.selectbox("세부 항목을 선택하세요.", subtopics_map.get(topic, ["세부 선택"]))
    if subtopic == "세부 선택": st.stop()

    students = fetch_students(subject, unit, subunit, topic, subtopic)
    if not students:
        st.warning("해당 세부 항목의 학생 기록이 없습니다.")
        st.stop()

    student_options = [f"{s[0]} ({s[1]}) / 코드: {s[2]}" for s in students]
    selected_student = st.selectbox("학생을 선택하세요:", student_options)
    selected_index = student_options.index(selected_student)
    number, name, code = students[selected_index]

    chat_data = fetch_chat(number, name, code, subject, unit, subunit, topic, subtopic)
    if chat_data:
        try:
            chat = json.loads(chat_data)
            st.write("### 학생의 대화 기록")
            for message in chat:
                role_label = "**You:**" if message["role"] == "user" else "**과학탐구 도우미:**"
                timestamp = f" ({message['timestamp']})" if "timestamp" in message else ""
                content = message["content"]
                parts = re.split(r"(@@@@@.*?@@@@@)", content, flags=re.DOTALL)
                for part in parts:
                    if part.startswith("@@@@@") and part.endswith("@@@@@"):
                        st.latex(part[5:-5].strip())
                    else:
                        cleaned = clean_inline_latex(part.strip())
                        if cleaned:
                            st.write(f"{role_label} {cleaned}{timestamp}" if role_label else cleaned)
                            role_label = ""
        except json.JSONDecodeError:
            st.error("대화 기록을 불러오는 데 실패했습니다.")
    else:
        st.warning("선택된 학생에 대한 대화 기록이 없습니다.")
else:
    st.error("비밀번호가 틀렸습니다.")