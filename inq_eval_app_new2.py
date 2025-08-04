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

# ===== 조건에 맞는 학생 목록 가져오기 =====
def fetch_students(subject, unit, subunit, topic):
    try:
        db = connect_to_db()
        cursor = db.cursor()
        query = """
        SELECT DISTINCT number, name, code
        FROM qna_unique_v2
        WHERE subject = %s AND unit = %s AND subunit = %s AND topic = %s
        ORDER BY number
        """
        cursor.execute(query, (subject, unit, subunit, topic))
        students = cursor.fetchall()
        cursor.close()
        db.close()
        return students
    except pymysql.MySQLError as e:
        st.error(f"데이터베이스 오류: {e}")
        return []

# ===== 학생의 대화 가져오기 =====
def fetch_chat(number, name, code, subject, unit, subunit, topic):
    try:
        db = connect_to_db()
        cursor = db.cursor()
        query = """
        SELECT chat
        FROM qna_unique_v2
        WHERE number = %s AND name = %s AND code = %s
          AND subject = %s AND unit = %s AND subunit = %s AND topic = %s
        """
        cursor.execute(query, (number, name, code, subject, unit, subunit, topic))
        result = cursor.fetchone()
        cursor.close()
        db.close()
        return result[0] if result else None
    except pymysql.MySQLError as e:
        st.error(f"데이터베이스 오류: {e}")
        return None

# ===== Streamlit UI =====
st.title("학생의 인공지능 사용 내역(교사용)")

password = st.text_input("비밀번호를 입력하세요", type="password")

if password == st.secrets["PASSWORD"]:
    # 1. 과목 선택
    subject = st.selectbox("과목을 선택하세요.", ["과목을 선택하세요.", "과학"])
    if subject == "과목을 선택하세요.":
        st.stop()

    # 2. 대단원 선택
    units = {
        "과학": ["대단원을 선택하세요.", "Ⅳ. 자극과 반응", "Ⅴ. 생식과 유전", "Ⅵ. 에너지 전환과 보존"]
    }
    unit = st.selectbox("대단원을 선택하세요.", units[subject])
    if unit == "대단원을 선택하세요.":
        st.stop()

    # 3. 중단원 선택
    subunits_map = {
        "Ⅳ. 자극과 반응": ["중단원을 선택하세요.", "1. 자극과 감각 기관", "2. 자극의 전달과 반응"],
        "Ⅴ. 생식과 유전": ["중단원을 선택하세요.", "1. 생장과 생식", "2. 유전"],
        "Ⅵ. 에너지 전환과 보존": ["중단원을 선택하세요.", "1. 역학적 에너지 전환과 보존", "2. 에너지의 전환과 이용"]
    }
    subunit = st.selectbox("중단원을 선택하세요.", subunits_map[unit])
    if subunit == "중단원을 선택하세요.":
        st.stop()

    # 4. 소단원 선택
    topics_map = {
        "1. 자극과 감각 기관": ["소단원을 선택하세요.", "01. 빛을 보는 눈", "02. 소리를 듣고 균형을 잡는 귀", "03. 냄새를 맡는 코, 맛을 보는 혀", "04. 여러 가지 자극을 받아들이는 피부"],
        "2. 자극의 전달과 반응": ["소단원을 선택하세요.", "01. 신경계는 신호를 전달해", "02. 자극에서 반응이 일어나기까지", "03. 호르몬은 우리 몸을 조절해", "04. 신경과 호르몬이 항상성을 유지해"],
        "1. 생장과 생식": ["소단원을 선택하세요.", "01. 생물이 자란다는 것은", "02. 염색체에 유전 정보가 있어", "03. 체세포는 어떻게 만들어질까", "04. 생식세포는 어떻게 만들어질까", "05. 정자와 난자가 만나 내가 되기까지"],
        "2. 유전": ["소단원을 선택하세요.", "01. 멘델의 유전 원리는", "02. 사람의 유전은 어떻게 연구할까", "03. 사람의 형질은 어떻게 유전될까"],
        "1. 역학적 에너지 전환과 보존": ["소단원을 선택하세요.", "01. 떨어지는 물체의 역학적 에너지는", "02. 던져 올린 물체의 역학적 에너지는"],
        "2. 에너지의 전환과 이용": ["소단원을 선택하세요.", "01. 움직이는 자석이 전기를 만들어", "02. 에너지는 전환되고 보존돼", "03. 전기 에너지는 다양하게 이용돼", "04. 전기 기구는 전기 에너지를 소비해"]
    }
    topic = st.selectbox("소단원을 선택하세요.", topics_map[subunit])
    if topic == "소단원을 선택하세요.":
        st.stop()

    # 5. 해당 소단원의 학생 목록 불러오기
    students = fetch_students(subject, unit, subunit, topic)
    if not students:
        st.warning("해당 소단원에 대한 학생 기록이 없습니다.")
        st.stop()

    student_options = [f"{s[0]} ({s[1]}) / 코드: {s[2]}" for s in students]
    selected_student = st.selectbox("학생을 선택하세요:", student_options)
    selected_index = student_options.index(selected_student)
    number, name, code = students[selected_index]

    # 6. 대화 조회
    chat_data = fetch_chat(number, name, code, subject, unit, subunit, topic)
    if chat_data:
        try:
            chat = json.loads(chat_data)

            # 표 데이터를 담을 리스트
            chat_table = []

            # 대화식 출력 (보기용)
            st.write("### 학생의 대화 기록 (대화식 보기)")
            for message in chat:
                role_label = "**You:**" if message["role"] == "user" else "**과학탐구 도우미:**"
                timestamp = f" ({message['timestamp']})" if "timestamp" in message else ""
                content = message["content"]

                parts = re.split(r"(@@@@@.*?@@@@@)", content, flags=re.DOTALL)
                cleaned_parts = []
                for part in parts:
                    if part.startswith("@@@@@") and part.endswith("@@@@@"):
                        st.latex(part[5:-5].strip())
                        cleaned_parts.append(part[5:-5].strip())
                    else:
                        cleaned = clean_inline_latex(part.strip())
                        if cleaned:
                            st.write(f"{role_label} {cleaned}{timestamp}" if role_label else cleaned)
                            cleaned_parts.append(cleaned)
                            role_label = ""  # 한 번만 출력

                # 표 데이터 추가
                chat_table.append({
                    "말한 사람": role_label.replace("**", "").replace(":", ""),
                    "대화 내용": " ".join(cleaned_parts),
                    "시간": message.get("timestamp", "")
                })

            # 복사용 표 출력
            st.write("### 학생의 대화 기록 (복사용 표)")
            import pandas as pd
            df = pd.DataFrame(chat_table)
            st.markdown(df.to_html(index=False), unsafe_allow_html=True)

        except json.JSONDecodeError:
            st.error("대화 기록을 불러오는 데 실패했습니다. JSON 형식이 잘못되었습니다.")
    else:
        st.warning("선택된 학생에 대한 대화 기록이 없습니다.")
else:
    st.error("비밀번호가 틀렸습니다.")