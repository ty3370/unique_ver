# 깃허브 unique_ver 리포지토리 사용

import streamlit as st
import pymysql
import json
from datetime import datetime
import google.generativeai as genai
import re
import hashlib
from zoneinfo import ZoneInfo
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "당신은 고등학생의 물리학 시뮬레이션 생성 도우미 역할을 합니다."
    "사용자 요청에 따라 p5.js에서 실행할 수 있는 자바스크립트 코드를 생성합니다."
    "[규칙]"
    "1. 코드에 주석은 하나도 넣지 마세요."
    "2. 코드를 만들 때는 반드시 위아래로 '+++++' 표시를 넣어 코드 구간을 구분하세요."
    "3. 모든 코드는 반드시 다음과 같은 형식을 엄격히 지켜야 합니다:"
    "+++++"
    "(p5.js 코드 내용)"
    "+++++"
    "4. 코드를 제공하며 수정에 관한 아주 간략한 설명을 한 줄 이내로 짧게 제공하세요."
    "5. createCanvas()의 가로 크기는 window.innerWidth * 0.9 를 절대 초과하지 말고, 세로 크기는 window.innerHeight * 0.75 를 절대 초과하지 마세요. 캔버스 크기를 하드코딩된 숫자로 지정하지 말고, 반드시 위 최대 크기 범위 내에서만 캔버스를 생성하세요."
    "이 규칙은 모든 코드 응답에 대해 예외 없이 적용되어야 하며, 어떠한 예외도 두어선 안 됩니다."
)

def connect_to_db():
    return pymysql.connect(
        host=st.secrets["DB_HOST"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_DATABASE"],
        charset="utf8mb4",
        autocommit=True
    )

def get_user_topics():
    number = st.session_state.get("user_number", "").strip()
    name = st.session_state.get("user_name", "").strip()
    code = st.session_state.get("user_code", "").strip()
    topics = []
    db = None
    try:
        db = connect_to_db()
        with db.cursor() as cursor:
            sql = "SELECT DISTINCT topic FROM qna_unique WHERE number = %s AND name = %s AND code = %s"
            cursor.execute(sql, (number, name, code))
            topics = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        st.error(f"프로젝트 목록을 불러오는 중 오류가 발생했습니다: {e}")
    finally:
        if db:
            db.close()
    return topics

def load_chat(topic):
    number = st.session_state.get("user_number", "").strip()
    name = st.session_state.get("user_name", "").strip()
    code = st.session_state.get("user_code", "").strip()
    db = None
    try:
        db = connect_to_db()
        with db.cursor() as cursor:
            sql = "SELECT chat FROM qna_unique WHERE number = %s AND name = %s AND code = %s AND topic = %s"
            cursor.execute(sql, (number, name, code, topic))
            result = cursor.fetchone()
            return json.loads(result[0]) if result else []
    except Exception as e:
        st.error(f"대화 내역을 불러오는 중 오류가 발생했습니다: {e}")
        return []
    finally:
        if db:
            db.close()

def save_chat(topic, chat):
    number = st.session_state.get("user_number", "").strip()
    name = st.session_state.get("user_name", "").strip()
    code = st.session_state.get("user_code", "").strip()
    db = None
    try:
        db = connect_to_db()
        with db.cursor() as cursor:
            sql = """
            INSERT INTO qna_unique (number, name, code, topic, chat, time)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE chat = VALUES(chat), time = VALUES(time)
            """
            val = (
                number,
                name,
                code,
                topic,
                json.dumps(chat, ensure_ascii=False),
                datetime.now()
            )
            cursor.execute(sql, val)
    except Exception as e:
        st.error(f"대화 저장 중 오류가 발생했습니다: {e}")
    finally:
        if db:
            db.close()

def render_p5(code):
    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.0/p5.min.js"></script>
<style>
html, body {
  margin: 0;
  padding: 0;
  background: transparent;
  overflow: auto;
}
#fs {
  position: fixed;
  top: 10px;
  right: 10px;
  z-index: 9999;
  background: rgba(255,255,255,0.85);
  border: 1px solid #ccc;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
}
:fullscreen,
:-webkit-full-screen {
  background: transparent !important;
}
canvas {
  background: transparent !important;
  display: block;
}
</style>
</style>
</head>
<body>

<button id="fs">Fullscreen</button>

<script>
__P5_CODE__
</script>

<script>
document.getElementById("fs").onclick = function () {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen();
  } else {
    document.exitFullscreen();
  }
};
</script>

</body>
</html>
"""
    return html.replace("__P5_CODE__", code)

def show_stage(message):
    st.markdown(f"""
    <div style='display: flex; align-items: center; font-size: 18px;'>
        <div class="loader" style="
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 16px;
            height: 16px;
            animation: spin 1s linear infinite;
            margin-right: 10px;
        "></div>
        <div>{message}</div>
    </div>

    <style>
    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}
    </style>
    """, unsafe_allow_html=True)

def page_1():
    st.title("🚀 물리학 시뮬레이션 제작 AI")
    st.subheader("학습자 정보를 입력하세요")
    st.session_state["user_number"] = st.text_input("학번", value=st.session_state.get("user_number", ""))
    st.session_state["user_name"] = st.text_input("이름", value=st.session_state.get("user_name", ""))
    st.session_state["user_code"] = st.text_input(
        "식별코드",
        value=st.session_state.get("user_code", ""),
        help="타인의 학번과 이름으로 접속하는 것을 방지하기 위해 자신만 기억할 수 있는 코드를 입력하세요."
    )
    st.markdown(
        "> 🌟 **“생각하건대 현재의 고난은 장차 우리에게 나타날 영광과 비교할 수 없도다”** — 로마서 8장 18절"
    )

    if st.button("접속하기"):
        if all(
            [
                st.session_state["user_number"],
                st.session_state["user_name"],
                st.session_state["user_code"],
            ]
        ):
            st.session_state["step"] = 2
            st.rerun()
        else:
            st.error("모든 정보를 입력해주세요.")

def page_2():
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

    if "loading" not in st.session_state:
        st.session_state["loading"] = False

    st.header(f"Project: {st.session_state['current_topic']}")

    top = st.container()
    bottom = st.container()

    with top:
        st.subheader("💬 AI Designer")
        chat_col, control_col = st.columns([2, 1])

        messages = st.session_state.get("messages", [])
        all_code_snippets = []
        code_counter = 0

        with chat_col:
            chat_container = st.container(height=420)

            for m in messages:
                with chat_container.chat_message(m["role"]):

                    def replace_code_block(match):
                        nonlocal code_counter
                        code_counter += 1
                        return f"> 💡 **시뮬레이션 코드 [Code Version {code_counter}] 생성 완료** 💡"

                    display_content = re.sub(
                        r"\+{5}.*?\+{5}",
                        replace_code_block,
                        m["content"],
                        flags=re.DOTALL,
                    )

                    st.markdown(display_content)

                    snippets = re.findall(r"\+{5}(.*?)\+{5}", m["content"], re.DOTALL)
                    for snippet in snippets:
                        all_code_snippets.append(snippet.strip())

        with control_col:
            st.markdown("#### ✏️ 입력 & 실행")

            msg_len = len(messages)
            input_key = f"prompt_area_{msg_len}"
            send_key = f"send_btn_{msg_len}"

            placeholder = st.empty()
            stage = st.empty()

            # =========================
            # 1️⃣ 입력 UI (로딩 아닐 때만)
            # =========================
            if not st.session_state["loading"]:
                with placeholder.container():
                    user_input = st.text_area(
                        "시뮬레이션 설명",
                        placeholder="시뮬레이션 내용을 설명해 주세요...",
                        height=140,
                        key=input_key,
                    )

                    if st.button(
                        "🤖 AI에게 요청",
                        key=send_key,
                        use_container_width=True,
                        type="primary",
                    ):
                        if user_input.strip():
                            st.session_state["pending_input"] = user_input
                            st.session_state["loading"] = True
                            st.rerun()
                        else:
                            st.warning("시뮬레이션 설명을 입력해 주세요.")

            if st.session_state["loading"]:
                placeholder.empty()
                stage.empty()
                show_stage("시뮬레이션 코드를 생성 중입니다...")
                st.markdown(" ")

                user_input = st.session_state.pop("pending_input", "")

                messages.append({"role": "user", "content": user_input})

                model = genai.GenerativeModel(
                    MODEL,
                    system_instruction=SYSTEM_PROMPT
                )

                history = []
                for m in messages[:-1]:
                    role = "model" if m["role"] == "assistant" else "user"
                    if not history or history[-1]["role"] != role:
                        history.append({"role": role, "parts": [m["content"]]})

                try:
                    response = model.generate_content(
                        history + [{"role": "user", "parts": [user_input]}]
                    )
                    answer = response.text

                    messages.append({"role": "assistant", "content": answer})

                    save_chat(
                        st.session_state["current_topic"],
                        messages
                    )

                    new_snippets = re.findall(
                        r"\+{5}(.*?)\+{5}",
                        answer,
                        re.DOTALL
                    )
                    if new_snippets:
                        st.session_state["current_code"] = new_snippets[-1].strip()

                    st.session_state["loading"] = False
                    stage.empty()
                    st.rerun()

                except Exception as e:
                    st.session_state["loading"] = False
                    stage.empty()
                    st.error(f"답변 생성 중 오류가 발생했습니다: {e}")

            if all_code_snippets:
                selected_ver = st.selectbox(
                    "코드 버전 선택",
                    range(len(all_code_snippets)),
                    format_func=lambda x: f"Code Version {x+1}",
                )

                if st.button(
                    "▶️ 선택한 코드 실행",
                    use_container_width=True
                ):
                    st.session_state["current_code"] = (
                        all_code_snippets[selected_ver]
                    )
                    st.rerun()

    with bottom:
        st.subheader("🖥️ Simulation Preview")

        if st.session_state.get("current_code"):

            st.markdown(
                """
                <style>
                iframe {
                    background: transparent !important;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            p5_html = render_p5(
                st.session_state["current_code"]
            )
            components.html(
                p5_html,
                height=650,
                scrolling=True
            )

            with st.expander("소스 코드 확인"):
                st.code(
                    st.session_state["current_code"],
                    language="javascript"
                )
        else:
            st.info("코드가 생성되면 이곳에 시뮬레이션이 나타납니다.")

if "step" not in st.session_state:
    st.session_state["step"] = 1

if st.session_state["step"] == 1:
    page_1()
elif st.session_state["step"] == 2:
    page_2()