import streamlit as st
import pymysql
import json
from datetime import datetime
from openai import OpenAI
import re

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
MODEL = "gpt-4o"

def prompt_chemistry():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 '화학 반응의 규칙과 에너지 변화' 단원을 지도하는 AI 튜터입니다. "
        "학생은 화학 반응식, 계수 맞추기, 발열/흡열 반응의 개념을 학습 중입니다. 학생의 수준은 중학생이며, 정답을 알려주기보다는 질문을 통해 유도해주세요. "
        "개념적 이해 부족, 실수, 오개념을 파악하여 친절하고 쉽게 설명하며, 가능한 경우 구체적인 예시를 활용해 설명하세요."
    )

def prompt_physics():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 '운동과 에너지' 단원을 지도하는 AI 튜터입니다. "
        "학생은 운동의 개념, 속력/가속도, 에너지 전환 및 보존 법칙에 대해 학습 중입니다. 학생의 이해 수준을 고려해, 직관적이고 단계적인 설명을 해주세요. "
        "정답을 직접적으로 제시하지 말고 질문을 활용하여 유도하는 방식으로 지도하세요."
    )

def prompt_earth_science():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 '기권과 날씨' 단원을 지도하는 AI 튜터입니다. "
        "학생은 기압, 습도, 구름 생성, 대기 대순환 등의 개념을 공부하고 있습니다. "
        "질문을 통해 개념을 유도하고, 대화식으로 흥미를 끌며 학습을 도와주세요. 예시는 실생활에 연관지어 설명하면 효과적입니다."
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

def load_chat(topic):
    number = st.session_state.get("user_number", "").strip()
    name = st.session_state.get("user_name", "").strip()
    code = st.session_state.get("user_code", "").strip()
    if not all([number, name, code]):
        return []
    try:
        db = connect_to_db()
        cursor = db.cursor()
        sql = """
        SELECT chat FROM qna_unique
        WHERE number = %s AND name = %s AND code = %s AND topic = %s
        """
        cursor.execute(sql, (number, name, code, topic))
        result = cursor.fetchone()
        cursor.close()
        db.close()
        if result:
            return json.loads(result[0])
    except Exception as e:
        st.error(f"DB 불러오기 오류: {e}")
    return []

def save_chat(topic, chat):
    number = st.session_state.get("user_number", "").strip()
    name = st.session_state.get("user_name", "").strip()
    code = st.session_state.get("user_code", "").strip()
    if not all([number, name, code]):
        return
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
        cursor.close()
        db.close()
    except Exception as e:
        st.error(f"DB 저장 오류: {e}")

def page_1():
    st.title("학습자 정보 입력")
    st.session_state["user_number"] = st.text_input("학번", value=st.session_state.get("user_number", ""))
    st.session_state["user_name"] = st.text_input("이름", value=st.session_state.get("user_name", ""))
    st.session_state["user_code"] = st.text_input("식별코드", value=st.session_state.get("user_code", ""))
    if st.button("다음"):
        if not all([
            st.session_state["user_number"].strip(),
            st.session_state["user_name"].strip(),
            st.session_state["user_code"].strip()
        ]):
            st.error("모든 정보를 입력해주세요.")
        else:
            st.session_state["step"] = 2
            st.rerun()

def page_2():
    st.title("모든 대화 내용은 저장되며, 교사가 열람할 수 있습니다.")
    st.markdown("""
    이 시스템은 인공지능을 활용한 과학 개념 학습 도우미입니다. 
    입력된 모든 대화는 저장되며, 교사가 확인할 수 있습니다. 
    학습 목적으로만 사용해주세요.
    """)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("이전"):
            st.session_state["step"] = 1
            st.rerun()
    with col2:
        if st.button("다음"):
            st.session_state["step"] = 3
            st.rerun()

def chatbot_tab(tab_label, topic):
    key_prefix = topic.replace(" ", "_")
    chat_key = f"chat_{key_prefix}"
    input_key = f"input_{key_prefix}"

    if chat_key not in st.session_state:
        st.session_state[chat_key] = load_chat(topic)

    st.subheader(f"주제: {topic}")

    for msg in st.session_state[chat_key]:
        if msg["role"] == "user":
            st.write(f"**You:** {msg['content']}")
        elif msg["role"] == "assistant":
            content = msg["content"]
            if "$" in content or "\\" in content:
                try:
                    st.markdown(f"**AI:**\n{content}", unsafe_allow_html=True)
                except:
                    st.write(f"**AI:** {content}")
            else:
                st.write(f"**AI:** {content}")

    user_input = st.text_area("입력: ", key=input_key)
    if st.button("전송", key=f"send_{key_prefix}"):
        messages = st.session_state[chat_key]
        if topic == "Ⅰ. 화학 반응의 규칙과 에너지 변화":
            system_prompt = prompt_chemistry()
        elif topic == "Ⅲ. 운동과 에너지":
            system_prompt = prompt_physics()
        elif topic == "Ⅱ. 기권과 날씨":
            system_prompt = prompt_earth_science()
        else:
            system_prompt = "과학 개념을 설명하는 AI입니다."

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}] + messages + [{"role": "user", "content": user_input}]
        )
        answer = response.choices[0].message.content
        messages.append({"role": "user", "content": user_input})
        messages.append({"role": "assistant", "content": answer})
        save_chat(topic, messages)
        st.rerun()

def page_3():
    st.title("탐구 활동 시작")
    tab_labels = ["Ⅰ. 화학 반응의 규칙과 에너지 변화", "Ⅲ. 운동과 에너지", "Ⅱ. 기권과 날씨"]
    selected_tab = st.selectbox("탐구 주제를 선택하세요", tab_labels, format_func=lambda x: f"🔹 {x}")

    if selected_tab == "Ⅰ. 화학 반응의 규칙과 에너지 변화":
        chatbot_tab(selected_tab, selected_tab)
    elif selected_tab == "Ⅲ. 운동과 에너지":
        chatbot_tab(selected_tab, selected_tab)
    elif selected_tab == "Ⅱ. 기권과 날씨":
        chatbot_tab(selected_tab, selected_tab)

    st.markdown("""<br><hr style='border-top:1px solid #bbb;'>""", unsafe_allow_html=True)
    if st.button("이전으로 돌아가기"):
        st.session_state["step"] = 2
        st.rerun()

if "step" not in st.session_state:
    st.session_state["step"] = 1

if st.session_state["step"] == 1:
    page_1()
elif st.session_state["step"] == 2:
    page_2()
elif st.session_state["step"] == 3:
    page_3()