import streamlit as st
import pymysql
import json
import re
import pandas as pd

# 환경 변수
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

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

# ===== 단원별 학생 목록 + 마지막 대화 시간 가져오기 =====
def fetch_students_by_topic(topic):
    try:
        db = connect_to_db()
        cursor = db.cursor()
        query = """
        SELECT number, name, code, MAX(updated_at) as last_chat
        FROM qna_unique
        WHERE topic = %s
        GROUP BY number, name, code
        ORDER BY number
        """
        cursor.execute(query, (topic,))
        students = cursor.fetchall()
        cursor.close()
        db.close()
        return students
    except pymysql.MySQLError as e:
        st.error(f"데이터베이스 오류: {e}")
        return []

# ===== 학생 대화 가져오기 =====
def fetch_chat(number, name, code, topic):
    try:
        db = connect_to_db()
        cursor = db.cursor()
        query = """
        SELECT chat
        FROM qna_unique
        WHERE number = %s AND name = %s AND code = %s AND topic = %s
        """
        cursor.execute(query, (number, name, code, topic))
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
    # 1. 단원 선택
    topics = [
        "Ⅰ. 화학 반응의 규칙과 에너지 변화",
        "Ⅲ. 운동과 에너지",
        "Ⅱ. 기권과 날씨"
    ]
    topic = st.selectbox("단원을 선택하세요.", topics)

    # 2. 해당 단원의 학생 목록 가져오기
    students = fetch_students_by_topic(topic)
    if not students:
        st.warning("해당 단원에 학생 기록이 없습니다.")
        st.stop()

    # 3. 학생 선택 (마지막 대화 시간 표시)
    student_options = [
        f"{s[0]} ({s[1]}) / {s[2]} / {s[3] if s[3] else '없음'}"
        for s in students
    ]
    selected_student = st.selectbox("학생을 선택하세요:", student_options)
    number, name, code, _ = students[student_options.index(selected_student)]

    # 4. 대화 불러오기
    chat_data = fetch_chat(number, name, code, topic)
    if chat_data:
        try:
            chat = json.loads(chat_data)
            st.write("### 학생의 대화 기록 (표 형식)")

            # 표 데이터를 담을 리스트
            chat_table = []

            for message in chat:
                role_label = "You" if message["role"] == "user" else "과학탐구 도우미"
                timestamp = message.get("timestamp", "")
                content = message["content"]

                # LaTeX 구문 처리
                parts = re.split(r"(@@@@@.*?@@@@@)", content, flags=re.DOTALL)
                cleaned_parts = []
                for part in parts:
                    if part.startswith("@@@@@") and part.endswith("@@@@@"):
                        cleaned_parts.append(part[5:-5].strip())  # LaTeX 내용 그대로
                    else:
                        cleaned_text = clean_inline_latex(part.strip())
                        if cleaned_text:
                            cleaned_parts.append(cleaned_text)

                cleaned_content = " ".join(cleaned_parts)
                
                chat_table.append({
                    "말한 사람": role_label,
                    "대화 내용": cleaned_content,
                    "시간": timestamp
                })

            # DataFrame 변환
            df = pd.DataFrame(chat_table)

            # 줄바꿈 가능한 표 스타일 적용
            st.markdown(
                """
                <style>
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                th, td {
                    text-align: left;
                    vertical-align: top;
                    white-space: pre-wrap;
                    word-break: break-word;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            # HTML 테이블로 렌더링
            st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)

        except json.JSONDecodeError:
            st.error("대화 기록을 불러오는 데 실패했습니다.")
    else:
        st.warning("선택된 학생에 대한 대화 기록이 없습니다.")
else:
    st.error("비밀번호가 틀렸습니다.")