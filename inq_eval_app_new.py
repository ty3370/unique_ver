import streamlit as st
import pymysql
import json

OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

def connect_to_db():
    return pymysql.connect(
        host=st.secrets["DB_HOST"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_DATABASE"],
        charset='utf8mb4'
    )

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
                    if message["role"] == "user":
                        st.write(f"**You:** {message['content']}")
                    elif message["role"] == "assistant":
                        st.write(f"**과학탐구 도우미:** {message['content']}")
            except json.JSONDecodeError:
                st.error("대화 기록을 불러오는 데 실패했습니다. JSON 형식이 잘못되었습니다.")
        else:
            st.warning("선택된 레코드에 대화 기록이 없습니다.")
    else:
        st.warning("데이터베이스에 저장된 내역이 없습니다.")
else:
    st.error("비밀번호가 틀렸습니다.")