import streamlit as st
import pymysql
import json
from datetime import datetime
from openai import OpenAI

st.set_page_config(
    page_title="세상을 위한 AI 프로젝트",
    page_icon="🤖",
    layout="wide"
)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
MODEL = "gpt-4o"

def connect_db():
    return pymysql.connect(
        host=st.secrets["DB_HOST"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_DATABASE"],
        charset="utf8mb4",
        autocommit=True
    )

def get_topics():
    db = connect_db()
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT topic FROM ai_project
            WHERE number=%s AND name=%s AND code=%s
            """,
            (
                st.session_state["number"],
                st.session_state["name"],
                st.session_state["code"]
            )
        )
        rows = cur.fetchall()
    db.close()
    return [r[0] for r in rows]

def get_prompt_versions(topic):
    db = connect_db()
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT prompt_no, prompt FROM ai_project
            WHERE number=%s AND name=%s AND code=%s AND topic=%s
            ORDER BY prompt_no
            """,
            (
                st.session_state["number"],
                st.session_state["name"],
                st.session_state["code"],
                topic
            )
        )
        rows = cur.fetchall()
    db.close()
    return rows

def save_new_prompt(topic, prompt):
    db = connect_db()
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(MAX(prompt_no),0)+1 FROM ai_project
            WHERE number=%s AND name=%s AND code=%s AND topic=%s
            """,
            (
                st.session_state["number"],
                st.session_state["name"],
                st.session_state["code"],
                topic
            )
        )
        next_no = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO ai_project
            (number,name,code,topic,prompt_no,prompt,chat)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                st.session_state["number"],
                st.session_state["name"],
                st.session_state["code"],
                topic,
                next_no,
                prompt,
                json.dumps([], ensure_ascii=False)
            )
        )
    db.close()

def load_chat(topic, prompt_no):
    db = connect_db()
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT chat FROM ai_project
            WHERE number=%s AND name=%s AND code=%s
              AND topic=%s AND prompt_no=%s
            """,
            (
                st.session_state["number"],
                st.session_state["name"],
                st.session_state["code"],
                topic,
                prompt_no
            )
        )
        row = cur.fetchone()
    db.close()
    return json.loads(row[0]) if row else []

def save_chat(topic, prompt_no, chat):
    db = connect_db()
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE ai_project
            SET chat=%s, time=%s
            WHERE number=%s AND name=%s AND code=%s
              AND topic=%s AND prompt_no=%s
            """,
            (
                json.dumps(chat, ensure_ascii=False),
                datetime.now(),
                st.session_state["number"],
                st.session_state["name"],
                st.session_state["code"],
                topic,
                prompt_no
            )
        )
    db.close()

def page_login():
    st.markdown(
        """
        <h1 style="text-align: center;">🤖 세상을 위한 AI 프로젝트</h1>
        <h5 style="text-align: center;">학습자 정보를 입력하세요</h5>
        """,
        unsafe_allow_html=True
    )

    left, center, right = st.columns([1, 2, 1])

    with center:
        st.markdown(
            """
            <div style="max-width: 520px; margin: auto;">
            """,
            unsafe_allow_html=True
        )

        st.session_state["number"] = st.text_input(
            "학번",
            value=st.session_state.get("number", "")
        )

        st.session_state["name"] = st.text_input(
            "이름",
            value=st.session_state.get("name", "")
        )

        st.session_state["code"] = st.text_input(
            "식별코드",
            value=st.session_state.get("code", ""),
            help="타인의 학번과 이름으로 접속하는 것을 방지하기 위해 자신만 기억할 수 있는 코드를 입력하세요."
        )

        st.markdown(
            """
            > ✋ **“네 손이 선을 베풀 힘이 있거든 마땅히 받을 자에게 베풀기를 아끼지 말며”** — 잠언 3장 27절
            """,
            unsafe_allow_html=True
        )

        btn_col_l, btn_col_c, btn_col_r = st.columns([1, 2, 1])

        with btn_col_c:
            if st.button("접속하기", use_container_width=True):
                if all([
                    st.session_state["number"],
                    st.session_state["name"],
                    st.session_state["code"]
                ]):
                    st.session_state["step"] = 2
                    st.rerun()
                else:
                    st.error("모든 정보를 입력해주세요.")

        st.markdown("</div>", unsafe_allow_html=True)

def page_main():
    with st.sidebar:
        st.header("📂 프로젝트")
        topics = get_topics()
        mode = st.radio("모드", ["기존 프로젝트", "새 프로젝트"])

        if mode == "기존 프로젝트" and topics:
            topic = st.selectbox("프로젝트 선택", topics)
        else:
            topic = st.text_input("새 프로젝트 이름")

        if st.button("프로젝트 열기"):
            if topic:
                st.session_state["topic"] = topic
                st.session_state.pop("prompt_no", None)
                st.rerun()

    if "topic" not in st.session_state:
        st.info("프로젝트를 선택하세요.")
        return

    st.header(f"📘 Project: {st.session_state['topic']}")

    st.subheader("⚙️ 시스템 프롬프트")

    new_prompt = st.text_area(
        "새 시스템 프롬프트",
        placeholder="시스템 프롬프트로 들어갈 내용을 입력하세요",
        height=120
    )

    if st.button("✅ 새 프롬프트 저장"):
        if new_prompt.strip():
            save_new_prompt(st.session_state["topic"], new_prompt)
            st.success("저장 완료")
            st.rerun()

    versions = get_prompt_versions(st.session_state["topic"])

    if not versions:
        st.warning("프롬프트를 먼저 추가하세요.")
        return

    prompt_map = {
        f"Prompt Version {no}": (no, text)
        for no, text in versions
    }

    keys = list(prompt_map.keys())
    selected = st.selectbox(
        "프롬프트 버전 선택",
        keys,
        index=len(keys) - 1
    )
    prompt_no, system_prompt = prompt_map[selected]
    st.session_state["prompt_no"] = prompt_no

    st.markdown("**선택된 시스템 프롬프트**")
    st.code(system_prompt)

    st.subheader("💬 Chat")

    chat = load_chat(st.session_state["topic"], prompt_no)

    for m in chat:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_input = st.chat_input("메시지를 입력하세요")

    if user_input:
        chat.append({
            "role": "user",
            "content": user_input,
            "time": datetime.now().isoformat()
        })

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                *chat
            ]
        )

        answer = response.choices[0].message.content
        chat.append({
            "role": "assistant",
            "content": answer,
            "time": datetime.now().isoformat()
        })
        save_chat(st.session_state["topic"], prompt_no, chat)
        st.rerun()

if "step" not in st.session_state:
    st.session_state["step"] = 1

if st.session_state["step"] == 1:
    page_login()
else:
    page_main()