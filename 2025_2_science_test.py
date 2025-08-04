import streamlit as st
import pymysql
import json
from datetime import datetime
from openai import OpenAI
import re
from zoneinfo import ZoneInfo

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
MODEL = "gpt-4o"

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

# ===== 소단원별 초기 프롬프트 =====
def prompt_Ⅳ_1_01():
    return (
        "Ⅳ. 자극과 반응 - 1. 자극과 감각 기관 - 01. 빛을 보는 눈"
    )

def prompt_Ⅳ_1_02():
    return (
        "Ⅳ. 자극과 반응 - 1. 자극과 감각 기관 - 02. 소리를 듣고 균형을 잡는 귀"
    )

def prompt_Ⅳ_1_03():
    return (
        "Ⅳ. 자극과 반응 - 1. 자극과 감각 기관 - 03. 냄새를 맡는 코, 맛을 보는 혀"
    )

def prompt_Ⅳ_1_04():
    return (
        "Ⅳ. 자극과 반응 - 1. 자극과 감각 기관 - 04. 여러 가지 자극을 받아들이는 피부"
    )

def prompt_Ⅳ_2_01():
    return (
        "Ⅳ. 자극과 반응 - 2. 자극의 전달과 반응 - 01. 신경계는 신호를 전달해"
    )

def prompt_Ⅳ_2_02():
    return (
        "Ⅳ. 자극과 반응 - 2. 자극의 전달과 반응 - 02. 자극에서 반응이 일어나기까지"
    )

def prompt_Ⅳ_2_03():
    return (
        "Ⅳ. 자극과 반응 - 2. 자극의 전달과 반응 - 03. 호르몬은 우리 몸을 조절해"
    )

def prompt_Ⅳ_2_04():
    return (
        "Ⅳ. 자극과 반응 - 2. 자극의 전달과 반응 - 04. 신경과 호르몬이 항상성을 유지해"
    )

def prompt_Ⅴ_1_01():
    return (
        "Ⅴ. 생식과 유전 - 1. 생장과 생식 - 01. 생물이 자란다는 것은"
    )

def prompt_Ⅴ_1_02():
    return (
        "Ⅴ. 생식과 유전 - 1. 생장과 생식 - 02. 염색체에 유전 정보가 있어"
    )

def prompt_Ⅴ_1_03():
    return (
        "Ⅴ. 생식과 유전 - 1. 생장과 생식 - 03. 체세포는 어떻게 만들어질까"
    )

def prompt_Ⅴ_1_04():
    return (
        "Ⅴ. 생식과 유전 - 1. 생장과 생식 - 04. 생식세포는 어떻게 만들어질까"
    )

def prompt_Ⅴ_1_05():
    return (
        "Ⅴ. 생식과 유전 - 1. 생장과 생식 - 05. 정자와 난자가 만나 내가 되기까지"
    )

def prompt_Ⅴ_2_01():
    return (
        "Ⅴ. 생식과 유전 - 2. 유전 - 01. 멘델의 유전 원리는"
    )

def prompt_Ⅴ_2_02():
    return (
        "Ⅴ. 생식과 유전 - 2. 유전 - 02. 사람의 유전은 어떻게 연구할까"
    )

def prompt_Ⅴ_2_03():
    return (
        "Ⅴ. 생식과 유전 - 2. 유전 - 03. 사람의 형질은 어떻게 유전될까"
    )

def prompt_Ⅵ_1_01():
    return (
        "Ⅵ. 에너지 전환과 보존 - 1. 역학적 에너지 전환과 보존 - 01. 떨어지는 물체의 역학적 에너지는"
    )

def prompt_Ⅵ_1_02():
    return (
        "Ⅵ. 에너지 전환과 보존 - 1. 역학적 에너지 전환과 보존 - 02. 던져 올린 물체의 역학적 에너지는"
    )

def prompt_Ⅵ_2_01():
    return (
        "Ⅵ. 에너지 전환과 보존 - 2. 에너지의 전환과 이용 - 01. 움직이는 자석이 전기를 만들어"
    )

def prompt_Ⅵ_2_02():
    return (
        "Ⅵ. 에너지 전환과 보존 - 2. 에너지의 전환과 이용 - 02. 에너지는 전환되고 보존돼"
    )

def prompt_Ⅵ_2_03():
    return (
        "Ⅵ. 에너지 전환과 보존 - 2. 에너지의 전환과 이용 - 03. 전기 에너지는 다양하게 이용돼"
    )

def prompt_Ⅵ_2_04():
    return (
        "Ⅵ. 에너지 전환과 보존 - 2. 에너지의 전환과 이용 - 04. 전기 기구는 전기 에너지를 소비해"
    )

# ===== DB 연결 =====
def connect_to_db():
    return pymysql.connect(
        host=st.secrets["DB_HOST"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_DATABASE"],
        charset="utf8mb4",
        autocommit=True
    )

def load_chat(subject, unit, subunit, topic):
    number = st.session_state.get("user_number", "").strip()
    name = st.session_state.get("user_name", "").strip()
    code = st.session_state.get("user_code", "").strip()
    if not all([number, name, code]):
        return []
    try:
        db = connect_to_db()
        cursor = db.cursor()
        sql = """
        SELECT chat FROM qna_unique_v2
        WHERE number = %s AND name = %s AND code = %s
        AND subject = %s AND unit = %s AND subunit = %s AND topic = %s
        """
        cursor.execute(sql, (number, name, code, subject, unit, subunit, topic))
        result = cursor.fetchone()
        cursor.close()
        db.close()
        if result:
            return json.loads(result[0])
    except Exception as e:
        st.error(f"DB 불러오기 오류: {e}")
    return []

def save_chat(subject, unit, subunit, topic, chat):
    number = st.session_state.get("user_number", "").strip()
    name = st.session_state.get("user_name", "").strip()
    code = st.session_state.get("user_code", "").strip()
    if not all([number, name, code]):
        return
    try:
        db = connect_to_db()
        cursor = db.cursor()
        sql = """
        INSERT INTO qna_unique_v2
        (number, name, code, subject, unit, subunit, topic, chat, time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE chat = VALUES(chat), time = VALUES(time)
        """
        val = (number, name, code, subject, unit, subunit, topic,
               json.dumps(chat, ensure_ascii=False), datetime.now())
        cursor.execute(sql, val)
        cursor.close()
        db.close()
    except Exception as e:
        st.error(f"DB 저장 오류: {e}")

# ===== 대화창 =====
def chatbot_tab(subject, unit, subunit, topic):
    key_prefix = "_".join([subject, unit, subunit, topic]).replace(" ", "_")
    chat_key = f"chat_{key_prefix}"

    if chat_key not in st.session_state:
        st.session_state[chat_key] = load_chat(subject, unit, subunit, topic)
    messages = st.session_state[chat_key]

    for msg in messages:
        if msg["role"] == "user":
            st.write(f"**You:** {msg['content']}")
        elif msg["role"] == "assistant":
            original = msg["content"]
            parts = re.split(r"(@@@@@.*?@@@@@)", original, flags=re.DOTALL)
            for part in parts:
                if part.startswith("@@@@@") and part.endswith("@@@@@"):
                    st.latex(part[5:-5].strip())
                else:
                    clean_text = clean_inline_latex(part)
                    if clean_text.strip():
                        if clean_text.startswith("http") and (".png" in clean_text or ".jpg" in clean_text or "imgur.com" in clean_text):
                            st.image(clean_text)
                        else:
                            st.write(f"**과학 도우미:** {clean_text.strip()}")

    input_key = f"user_input_{key_prefix}"
    loading_key = f"loading_{key_prefix}"
    if loading_key not in st.session_state:
        st.session_state[loading_key] = False

    if not st.session_state[loading_key]:
        user_input = st.text_area("입력: ", value="", key=f"textarea_{key_prefix}_{len(messages)}")
        if st.button("전송", key=f"send_{key_prefix}_{len(messages)}") and user_input.strip():
            st.session_state[loading_key] = True
            st.session_state[input_key] = user_input
            st.rerun()
    else:
        st.markdown("<br><i>✏️ 과학 도우미가 답변을 생성 중입니다...</i>", unsafe_allow_html=True)

    if st.session_state[loading_key]:
        user_input = st.session_state.get(input_key, "").strip()
        func_name = f"prompt_{unit.split('.')[0]}_{subunit.split('.')[0]}_{topic.split('.')[0]}"
        system_prompt = globals().get(func_name, lambda: "과학 개념을 설명하는 AI입니다.")()

        timestamp = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}] + messages + [{"role": "user", "content": user_input}],
        )
        answer = response.choices[0].message.content

        messages.append({"role": "user", "content": user_input, "timestamp": timestamp})
        messages.append({"role": "assistant", "content": answer})
        save_chat(subject, unit, subunit, topic, messages)

        st.session_state.pop(input_key, None)
        st.session_state[loading_key] = False
        st.rerun()

# ===== 페이지 =====
def page_1():
    st.title("2025-2학기 과학 도우미")
    st.write("학습자 정보를 입력하세요.")
    st.session_state["user_number"] = st.text_input("학번", value=st.session_state.get("user_number", ""))
    st.session_state["user_name"] = st.text_input("이름", value=st.session_state.get("user_name", ""))
    st.session_state["user_code"] = st.text_input(
        "식별코드",
        value=st.session_state.get("user_code", ""),
        help="타인의 학번과 이름으로 접속하는 것을 방지하기 위해 자신만 기억할 수 있는 코드를 입력하세요."
    )
    st.markdown("""
    > 🌟 **“생각하건대 현재의 고난은 장차 우리에게 나타날 영광과 비교할 수 없도다”**  
    > — 로마서 8장 18절
    """)
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
    st.title("⚠️모든 대화 내용은 저장되며, 교사가 열람할 수 있습니다.")
    st.write(
       """  
        이 시스템은 중3 학생들을 위한 AI 과학 학습 도우미입니다.

        입력된 모든 대화는 저장되며, 교사가 확인할 수 있습니다.

        부적절한 언어나 용도로 사용하는 것을 삼가주시고, 학습 목적으로만 사용하세요.

        ❗AI의 응답은 부정확할 수 있으므로, 정확한 정보는 선생님께 확인하세요.

        계정 찾기/문의/피드백: 창의융합부 민태호
        """)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("다음"):
            st.session_state["step"] = 3
            st.rerun()

def page_3():
    st.title("단원 학습")

    subject = st.selectbox("과목을 선택하세요.", ["과목을 선택하세요.", "과학"])
    if subject == "과목을 선택하세요.":
        return

    units = {
        "과학": ["대단원을 선택하세요.", "Ⅳ. 자극과 반응", "Ⅴ. 생식과 유전", "Ⅵ. 에너지 전환과 보존"]
    }
    unit = st.selectbox("대단원을 선택하세요.", units[subject])
    if unit == "대단원을 선택하세요.":
        return

    subunits_map = {
        "Ⅳ. 자극과 반응": ["중단원을 선택하세요.", "1. 자극과 감각 기관", "2. 자극의 전달과 반응"],
        "Ⅴ. 생식과 유전": ["중단원을 선택하세요.", "1. 생장과 생식", "2. 유전"],
        "Ⅵ. 에너지 전환과 보존": ["중단원을 선택하세요.", "1. 역학적 에너지 전환과 보존", "2. 에너지의 전환과 이용"]
    }
    subunit = st.selectbox("중단원을 선택하세요.", subunits_map[unit])
    if subunit == "중단원을 선택하세요.":
        return

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
        return

    chatbot_tab(subject, unit, subunit, topic)

# ===== 페이지 라우팅 =====
if "step" not in st.session_state:
    st.session_state["step"] = 1

if st.session_state["step"] == 1:
    page_1()
elif st.session_state["step"] == 2:
    page_2()
elif st.session_state["step"] == 3:
    page_3()
