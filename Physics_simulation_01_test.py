import streamlit as st
import pymysql
import json
from datetime import datetime
import google.generativeai as genai
import re
from zoneinfo import ZoneInfo
import streamlit.components.v1 as components

# 페이지 설정 (가장 상단에 위치해야 합니다)
st.set_page_config(layout="wide")

# API 설정
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
MODEL = "gemini-1.5-flash" 

# 시스템 프롬프트 설정
SYSTEM_PROMPT = (
    "당신은 물리학 시뮬레이션 생성 도우미 역할을 합니다.\n"
    "사용자 요청에 따라 p5.js에서 실행할 수 있는 자바스크립트 코드를 생성합니다.\n\n"
    "[규칙]\n"
    "1. 코드에 주석은 하나도 넣지 마세요.\n"
    "2. 코드를 만들 때는 반드시 위아래로 '\\n\\n+++++\\n\\n' 표시를 넣어 코드 구간을 구분하세요.\n"
    "3. 모든 코드는 반드시 다음과 같은 형식을 엄격히 지켜야 합니다:\n\n"
    "\\n\\n+++++\\n\\n(p5.js 코드 내용)\\n\\n+++++\\n\\n\n"
    "이 규칙은 모든 코드 응답에 대해 예외 없이 적용되어야 하며, 어떠한 예외도 두어선 안 됩니다."
)

# 데이터베이스 연결 함수
def connect_to_db():
    return pymysql.connect(
        host=st.secrets["DB_HOST"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_DATABASE"],
        charset="utf8mb4",
        autocommit=True
    )

# 유저 토픽 목록 불러오기
def get_user_topics():
    number = st.session_state.get("user_number", "").strip()
    name = st.session_state.get("user_name", "").strip()
    code = st.session_state.get("user_code", "").strip()
    topics = []
    try:
        db = connect_to_db()
        cursor = db.cursor()
        sql = "SELECT DISTINCT topic FROM qna_unique WHERE number = %s AND name = %s AND code = %s"
        cursor.execute(sql, (number, name, code))
        topics = [row[0] for row in cursor.fetchall()]
        db.close()
    except: pass
    return topics

# 특정 토픽의 대화 내역 불러오기
def load_chat(topic):
    number = st.session_state.get("user_number", "").strip()
    name = st.session_state.get("user_name", "").strip()
    code = st.session_state.get("user_code", "").strip()
    try:
        db = connect_to_db()
        cursor = db.cursor()
        sql = "SELECT chat FROM qna_unique WHERE number = %s AND name = %s AND code = %s AND topic = %s"
        cursor.execute(sql, (number, name, code, topic))
        result = cursor.fetchone()
        db.close()
        return json.loads(result[0]) if result else []
    except: return []

# 대화 내역 저장하기
def save_chat(topic, chat):
    number = st.session_state.get("user_number", "").strip()
    name = st.session_state.get("user_name", "").strip()
    code = st.session_state.get("user_code", "").strip()
    try:
        db = connect_to_db()
        cursor = db.cursor()
        sql = """
        INSERT INTO qna_unique (number, name, code, topic, chat, time) 
        VALUES (%s, %s, %s, %s, %s, %s) 
        ON DUPLICATE KEY UPDATE chat = VALUES(chat), time = VALUES(time)
        """
        val = (number, name, code, topic, json.dumps(chat, ensure_ascii=False), datetime.now())
        cursor.execute(sql, val)
        db.close()
    except: pass

# p5.js 실시간 실행기
def render_p5(code):
    p5_html = f"""
    <html>
    <head><script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.4.1/p5.js"></script></head>
    <body style="margin:0; background:#f0f0f0; overflow:hidden; display:flex; justify-content:center; align-items:center;">
        <script>{code}</script>
    </body>
    </html>
    """
    components.html(p5_html, height=500)

# 1페이지: 정보 입력
def page_1():
    st.title("🚀 물리학 시뮬레이션 제작 AI")
    st.subheader("학습자 정보를 입력하세요")
    st.session_state["user_number"] = st.text_input("학번", value=st.session_state.get("user_number", ""))
    st.session_state["user_name"] = st.text_input("이름", value=st.session_state.get("user_name", ""))
    st.session_state["user_code"] = st.text_input("식별코드", type="password")
    
    if st.button("접속하기"):
        if all([st.session_state["user_number"], st.session_state["user_name"], st.session_state["user_code"]]):
            st.session_state["step"] = 2
            st.rerun()
        else:
            st.error("모든 정보를 입력해주세요.")

# 2페이지: 메인 워크스페이스 (채팅 및 시뮬레이션)
def page_2():
    # 사이드바: 프로젝트 관리
    with st.sidebar:
        st.title("📂 프로젝트 관리")
        existing_topics = get_user_topics()
        mode = st.radio("작업 선택", ["기존 프로젝트 불러오기", "새 프로젝트 만들기"])
        
        if mode == "기존 프로젝트 불러오기" and existing_topics:
            current_topic = st.selectbox("프로젝트 선택", existing_topics)
        else:
            current_topic = st.text_input("새 프로젝트 제목 입력")
            
        if st.button("프로젝트 시작/변경"):
            if current_topic:
                st.session_state["current_topic"] = current_topic
                st.session_state["messages"] = load_chat(current_topic)
                st.session_state["current_code"] = ""
                st.rerun()
            else:
                st.warning("제목을 입력하거나 선택하세요.")

    if "current_topic" not in st.session_state:
        st.info("왼쪽 사이드바에서 프로젝트를 선택하거나 새로 생성해 주세요.")
        return

    st.header(f"Project: {st.session_state['current_topic']}")
    col_chat, col_preview = st.columns([1, 1])

    # 좌측: AI 채팅 화면
    with col_chat:
        st.subheader("💬 AI Designer")
        chat_container = st.container(height=500)
        
        messages = st.session_state.get("messages", [])
        all_code_snippets = []

        for m in messages:
            with chat_container.chat_message(m["role"]):
                st.write(m["content"])
                # +++++ 구분자 사이의 코드 추출
                snippets = re.findall(r"\+\+\+\+\+(.*?)\+\+\+\+\+", m["content"], re.DOTALL)
                for snippet in snippets:
                    all_code_snippets.append(snippet.strip())

        # 코드 버전 선택 실행
        if all_code_snippets:
            st.divider()
            selected_ver = st.selectbox(
                "실행할 코드 버전 선택", 
                range(len(all_code_snippets)),
                format_func=lambda x: f"Code Version {x+1}"
            )
            if st.button("▶️ 선택한 코드 실행"):
                st.session_state["current_code"] = all_code_snippets[selected_ver]

        # 사용자 입력
        if user_input := st.chat_input("시뮬레이션 내용을 설명해 주세요..."):
            messages.append({"role": "user", "content": user_input})
            
            model = genai.GenerativeModel(MODEL, system_instruction=SYSTEM_PROMPT)
            history = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [m["content"]]} for m in messages[:-1]]
            
            try:
                response = model.generate_content(history + [{"role": "user", "parts": [user_input]}])
                answer = response.text
                messages.append({"role": "assistant", "content": answer})
                
                save_chat(st.session_state["current_topic"], messages)
                
                # 최신 코드 자동 로드
                new_snippets = re.findall(r"\+\+\+\+\+(.*?)\+\+\+\+\+", answer, re.DOTALL)
                if new_snippets:
                    st.session_state["current_code"] = new_snippets[-1].strip()
                st.rerun()
            except Exception as e:
                st.error(f"오류 발생: {e}")

    # 우측: p5.js 실행 화면
    with col_preview:
        st.subheader("🖥️ Simulation Preview")
        if st.session_state.get("current_code"):
            render_p5(st.session_state["current_code"])
            with st.expander("소스 코드 확인"):
                st.code(st.session_state["current_code"], language="javascript")
        else:
            st.info("코드가 생성되면 이곳에 시뮬레이션이 나타납니다.")

# 페이지 라우팅 제어
if "step" not in st.session_state:
    st.session_state["step"] = 1

if st.session_state["step"] == 1:
    page_1()
elif st.session_state["step"] == 2:
    page_2()