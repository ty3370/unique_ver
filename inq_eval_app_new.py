import streamlit as st
import pymysql
import json
import re

# 환경 변수
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# LaTeX 텍스트 정리 함수
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

# DB 연결
def connect_to_db():
    return pymysql.connect(
        host=st.secrets["DB_HOST"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_DATABASE"],
        charset='utf8mb4'
    )

# 전체 기록 가져오기
def fetch_records():
    try:
        db = connect_to_db()
        cursor = db.cursor()
        query = """
        SELECT id, number, name, code, topic, time 
        FROM qna_unique
        ORDER BY
          CASE WHEN number >= 10300 AND number < 10400 THEN 0 ELSE 1 END,
          number
        """
        cursor.execute(query)
        records = cursor.fetchall()
        cursor.close()
        db.close()
        return records
    except pymysql.MySQLError as e:
        st.error(f"데이터베이스 오류: {e}")
        return []

# ID로 개별 대화 가져오기
def fetch_record_by_id(record_id):
    try:
        db = connect_to_db()
        cursor = db.cursor()
        cursor.execute("SELECT chat FROM qna_unique WHERE id = %s", (record_id,))
        record = cursor.fetchone()
        cursor.close()
        db.close()
        return record
    except pymysql.MySQLError as e:
        st.error(f"데이터베이스 오류: {e}")
        return None

# Streamlit UI
st.title("학생의 인공지능 사용 내역(교사용)")

password = st.text_input("비밀번호를 입력하세요", type="password")

if password == st.secrets["PASSWORD"]:
    records = fetch_records()

    if records:
        record_options = [
            f"{record[1]} ({record[2]}) / 코드: {record[3]} / 주제: {record[4]} - {record[5]}"
            for record in records
        ]
        selected_record = st.selectbox("내역을 선택하세요:", record_options)
        selected_record_id = records[record_options.index(selected_record)][0]

        record = fetch_record_by_id(selected_record_id)
        if record and record[0]:
            try:
                chat = json.loads(record[0])
                st.write("### 학생의 대화 기록")
                for message in chat:
                    role_label = "**You:**" if message["role"] == "user" else "**과학탐구 도우미:**"
                    content = message["content"]
                    parts = re.split(r"(@@@@@.*?@@@@@)", content, flags=re.DOTALL)

                    for part in parts:
                        if part.startswith("@@@@@") and part.endswith("@@@@@"):
                            st.latex(part[5:-5].strip())
                        else:
                            cleaned = clean_inline_latex(part.strip())
                            if cleaned:
                                st.write(f"{role_label} {cleaned}" if role_label else cleaned)
                                role_label = ""  # 한 번만 출력
            except json.JSONDecodeError:
                st.error("대화 기록을 불러오는 데 실패했습니다. JSON 형식이 잘못되었습니다.")
        else:
            st.warning("선택된 레코드에 대화 기록이 없습니다.")
    else:
        st.warning("데이터베이스에 저장된 내역이 없습니다.")
else:
    st.error("비밀번호가 틀렸습니다.")