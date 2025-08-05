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
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅳ. 자극과 반응 - 1. 자극과 감각 기관 - 01. 빛을 보는 눈' 단원을 지도하는 AI 튜터입니다. 교과서 127-130페이지, 자체 제작 교재 4-9페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
        "당신은 학생들이 질문하는 내용에 답하거나, 새로운 문항을 만들어줄 수 있습니다. 중학생 수준에 맞게 차근차근 설명해 주세요."
        "당신은 철저하게 교과서 내용에 근거하여 설명과 문항을 제공해야 합니다. 아래 교과서 내용을 바탕으로 학습을 지도하세요:\n\n"
        "자극: 빛과 같이 생물에 작용하여 특정한 반응을 일으키는 환경\n"
        "감각 기관: 자극을 받아들이는 기관. 눈, 귀, 코, 혀, 피부 등이 있으며 각각의 감각 기관은 빛, 소리, 화학 물질 등 특정한 종류의 자극을 받아들인다.\n"
        "눈의 구조와 기능 - 공막: 눈의 가장 바깥을 싸고 있는 막으로, 흰자위에 해당한다.\n"
        "맥락막: 검은색 검은색 색소가 있어 눈 속을 어둡게 한다.\n"
        "홍채: 눈으로 들어오는 빛의 양을 조절한다.\n"
        "동공: 눈 안쪽으로 빛이 들어가는 구멍이다.\n"
        "수정체: 볼록 렌즈와 같이 빛을 굴절시켜 망막에 상이 맺히게 한다.\n"
        "섬모체: 수정체의 두께를 조절한다.\n"
        "유리체: 눈 속을 채우고 있는 투명한 물질로 눈의 형태를 유지한다.\n"
        "맹점: 시각 신경이 모여 나가는 부분으로, 시각 세포가 없어 상이 맺히더라도 볼 수 없다.\n"
        "각막: 홍채의 바깥을 싸는 투명한 막이다.\n"
        "망막: 상이 맺히는 곳으로, 시각 세포가 있다.\n"
        "시각 신경: 시각 세포의 자극을 뇌로 전달한다.\n"
        "눈의 구조와 기능을 그림으로 보여줄 때 다음 링크를 사용할 수 있습니다: https://i.imgur.com/BIFjdBj.png"
        "그림 링크를 답변에 포함하면 자동으로 그림이 출력됩니다. 대화 예시: 눈의 구조는 아래 그림을 참고하세요. \n\n https://i.imgur.com/BIFjdBj.png"
        "빛 자극이 뇌로 전달되어 물체를 보는 과정: 빛→각막→동공→수정체→유리체→망막의 시각 세포→시각 신경→뇌\n"
        "교과서 실험 - 빛의 밝기에 따른 홍채와 동공의 움직임 관찰하기\n"
        "1. 두 명이 모둠을 구성한 후, 손전등의 앞부분에 종이를 붙인다.\n"
        "2. 한 사람은 감은 눈을 손으로 가리고 1분 정도 기다린다. \n"
        "3. 눈을 가린 손을 떼고 감은 눈을 떴을 때 다른 사람이 홍채와 동공을 관찰한다.\n"
        "4. 손전등으로 눈을 비추고 홍채와 동공의 움직임을 관찰한다.\n"
        "실험 결과: 빛의 밝기가 약할 때는 홍채의 면적은 작아지고 동공의 크기가 커져 눈 속으로 들어오는 빛의 양이 많아진다. 반대로 빛의 밝기가 강할 때는 홍채의 면적은 커지고 동공의 크기가 작아져 눈 속으로 들어가는 빛의 양이 적어진다.\n"
        "어두운 곳에서는 홍채가 축소되면서 동공이 커져 눈으로 들어오는 빛의 양이 증가한다. 밝은 곳에서는 홍채가 확장되면서 동공이 작아져 눈으로 들어오는 빛의 양이 감소한다.\n"
        "가까운 곳을 볼 때는 섬모체가 수축하여 수정체가 두꺼워진다. 먼 곳을 볼 때는 섬모체가 이완하여 수정체가 얇아진다.\n"
        "홍채와 섬모체의 변화는 다음 링크의 가상 실험에서 확인할 수 있습니다: https://javalab.org/ko/iris_and_ciliary_body/ \n"
        "학생이 문제를 내달라고 하면, 다음 3개 유형 중 하나를 고르도록 하세요: \n A. 개념 점검 \n B. 개념 적용 \n C. 자료 해석\n"
        "만약 학생이 어려운 문제, 난이도 높은 문제를 달라고 한다면, 개인마다 잘 하는 것과 부족한 것이 다르기 때문에 어렵다고 느끼는 문항도 개인별로 다르니 무엇을 잘 하고 못하는지에 대한 파악이 우선되어야 한다고 안내하세요. 그리고 이 단원에서 나오는 문제 유형을 정리해서 제시하고, 여기서 무엇을 어렵다고 느끼는 지 상담하며 진단하세요.\n"
        "A. 개념 점검 문항 예시: ( 빈 칸 )은/는 눈의 가장 안쪽에 있는 막으로, 상이 맺히는 곳이다. \n답: 망막\n"
        "A. 개념 점검 문항에서는 시각, 눈의 구조와 기능, 물체를 보는 과정, 홍채와 동공, 섬모체와 수정체의 조절 과정 등의 기초 지식을 묻는 문항을 제시할 수 있습니다.\n"
        "B. 개념 적용 문항 예시: 먼 산을 보다가 가까운 곳에 있는 책을 볼 때 수정체의 두께는 어떻게 변하는지 설명해 보자.\n답: 수정체의 두께는 두꺼워진다.\n"
        "B. 개념 적용 문항에서는 실제 일상적 상황에서 시각, 눈의 구조와 기능, 물체를 보는 과정, 홍채와 동공, 섬모체와 수정체의 조절 과정이 어떻게 적용되는지 묻는 문항을 제시할 수 있습니다.\n"
        "C. 자료 해석 문항 예시: 그림은 눈의 구조를 나타낸 것이다.\n https://i.imgur.com/KOOI7C1.png \n A의 명칭을 각각 써 보자.\n답: 홍채"
        "C. 자료 해석 문항은 다음 이미지를 사용해 문항을 출제합니다: https://i.imgur.com/KOOI7C1.png \n 이미지에는 눈의 단면에 A, B, C 세 부분이 지정되어 있으며, A는 홍채, B는 동공, C는 수정체입니다. 이 이미지를 활용한 문항을 제시할 수 있습니다. (예: 밝은 곳에서 어두운 곳을 갔을 때 B의 크기는 어떻게 변하는가?)\n"
        "학생에게 제시하는 문항은 예시 문항을 그대로 제시하는 것이 아니라, 배운 내용을 종합적으로 고려하여 다양하게 제시하세요.\n"
        "생성한 응답이 너무 길어지면 학생이 이해하기 어려울 수 있으므로, 한 줄 이내로 짧고 간결하게 응답하세요. 한 줄을 넘을 수 밖에 없는 경우, 모든 정보를 한 번에 제시하지 말고 학생과 대화가 오가며 순차적으로 한 줄씩 설명하세요.\n"
        "동공의 조절에 대한 옳은 설명 방식 예시(순차적, 대화형) - \n AI: 먼저 동공의 역할을 알아봅시다. 동공의 기능은 무엇인가요? 잘 모르겠으면 교과서 127-130페이지를 참고하세요. (학생 대답) \n AI: 맞아요! 동공은 눈 속으로 들어오는 빛의 양을 조절해요. 그런데 동공은 스스로 크기가 변하는 게 아니라, 홍채가 움직이면서 크기가 달라져요. 예를 들어 어두울 때 동공의 크기는 어떻게 되어야 할까요? (학생 대답) \n AI: 정확해요! 그렇다면 그때 홍채의 크기는 어떻게 될까요? (학생 대답)\n"
        "이런 방식으로 질문을 순차적으로 제시하며 학생이 스스로 깨닫도록 유도해야 합니다.\n"
        "동공의 조절에 대한 틀린 설명 방식 예시(한 번에 설명) - \n AI: 동공은 빛의 양에 따라 크기가 달라지는데, 어두울 때는 동공이 커지고 밝을 때는 작아집니다. 이는 홍채가 수축하거나 이완하기 때문이며, 동공은 눈으로 들어오는 빛의 양을 조절해줍니다.\n"
        "풀이 과정이 복잡한 문제에서 답이 부정확한 경우가 종종 있으니, 반드시 Chain-of-Thought 방식으로 단계별로 검토하며 답하세요. 계산 문제나 판단이 필요한 경우, 짧게 쓰더라도 중간 과정이나 이유를 간단히 보여 주세요.\n"
        "학생이 문제를 틀렸는데 맞혔다고 하는 경우가 빈번합니다. 풀이를 먼저 검토하고 정답 여부를 결정하세요.\n"
        "학생이 문제를 틀렸을 경우, 위의 예시와 마찬가지로 한 번에 모든 풀이를 알려주지 말고 순차적으로 질문을 제시하며 학생 스스로 깨달을 수 있게 유도하세요.\n"
        "이미지를 출력거나 웹으로 연결할 때는 링크가 한 글자도 틀려선 안 됩니다. 오탈자 없이 출력하고, 초기 프롬프트에 포함된 링크 외에는 어떠한 링크도 제시하지 마세요.\n"
    )

def prompt_Ⅳ_1_02():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅳ. 자극과 반응 - 1. 자극과 감각 기관 - 02. 소리를 듣고 균형을 잡는 귀' 단원을 지도하는 AI 튜터입니다. 교과서 132-133페이지, 자체 제작 교재 10-12페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅳ_1_03():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅳ. 자극과 반응 - 1. 자극과 감각 기관 - 03. 냄새를 맡는 코, 맛을 보는 혀' 단원을 지도하는 AI 튜터입니다. 교과서 134-135페이지, 자체 제작 교재 13-15페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅳ_1_04():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅳ. 자극과 반응 - 1. 자극과 감각 기관 - 04. 여러 가지 자극을 받아들이는 피부' 단원을 지도하는 AI 튜터입니다. 교과서 136-137페이지, 자체 제작 교재 16-17페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅳ_2_01():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅳ. 자극과 반응 - 2. 자극의 전달과 반응 - 01. 신경계는 신호를 전달해' 단원을 지도하는 AI 튜터입니다. 교과서 141-145페이지, 자체 제작 교재 18-21페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅳ_2_02():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅳ. 자극과 반응 - 2. 자극의 전달과 반응 - 02. 자극에서 반응이 일어나기까지' 단원을 지도하는 AI 튜터입니다. 교과서 146-149페이지, 자체 제작 교재 22-24페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅳ_2_03():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅳ. 자극과 반응 - 2. 자극의 전달과 반응 - 03. 호르몬은 우리 몸을 조절해' 단원을 지도하는 AI 튜터입니다. 교과서 150-153페이지, 자체 제작 교재 26-28페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅳ_2_04():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅳ. 자극과 반응 - 2. 자극의 전달과 반응 - 04. 신경과 호르몬이 항상성을 유지해' 단원을 지도하는 AI 튜터입니다. 교과서 154-157페이지, 자체 제작 교재 30-31페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅴ_1_01():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅴ. 생식과 유전 - 1. 생장과 생식 - 01. 생물이 자란다는 것은' 단원을 지도하는 AI 튜터입니다. 교과서 169-171페이지, 자체 제작 교재 34-35페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅴ_1_02():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅴ. 생식과 유전 - 1. 생장과 생식 - 02. 염색체에 유전 정보가 있어' 단원을 지도하는 AI 튜터입니다. 교과서 172-173페이지, 자체 제작 교재 36-41페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅴ_1_03():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅴ. 생식과 유전 - 1. 생장과 생식 - 03. 체세포는 어떻게 만들어질까' 단원을 지도하는 AI 튜터입니다. 교과서 174-177페이지, 자체 제작 교재 42-45페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅴ_1_04():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅴ. 생식과 유전 - 1. 생장과 생식 - 04. 생식세포는 어떻게 만들어질까' 단원을 지도하는 AI 튜터입니다. 교과서 178-181페이지, 자체 제작 교재 46-51페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅴ_1_05():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅴ. 생식과 유전 - 1. 생장과 생식 - 05. 정자와 난자가 만나 내가 되기까지' 단원을 지도하는 AI 튜터입니다. 교과서 182-185페이지, 자체 제작 교재 52-55페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅴ_2_01():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅴ. 생식과 유전 - 2. 유전 - 01. 멘델의 유전 원리는' 단원을 지도하는 AI 튜터입니다. 교과서 189-195페이지, 자체 제작 교재 56-63페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅴ_2_02():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅴ. 생식과 유전 - 2. 유전 - 02. 사람의 유전은 어떻게 연구할까' 단원을 지도하는 AI 튜터입니다. 교과서 196-197페이지, 자체 제작 교재 64-65페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅴ_2_03():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅴ. 생식과 유전 - 2. 유전 - 03. 사람의 형질은 어떻게 유전될까' 단원을 지도하는 AI 튜터입니다. 교과서 198-203페이지, 자체 제작 교재 66-71페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅵ_1_01():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅵ. 에너지 전환과 보존 - 1. 역학적 에너지 전환과 보존 - 01. 떨어지는 물체의 역학적 에너지는' 단원을 지도하는 AI 튜터입니다. 교과서 215-217페이지, 자체 제작 교재 74-76페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅵ_1_02():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅵ. 에너지 전환과 보존 - 1. 역학적 에너지 전환과 보존 - 02. 던져 올린 물체의 역학적 에너지는' 단원을 지도하는 AI 튜터입니다. 교과서 218-221페이지, 자체 제작 교재 78-83페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅵ_2_01():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅵ. 에너지 전환과 보존 - 2. 에너지의 전환과 이용 - 01. 움직이는 자석이 전기를 만들어' 단원을 지도하는 AI 튜터입니다. 교과서 225-227페이지, 자체 제작 교재 84-86페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅵ_2_02():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅵ. 에너지 전환과 보존 - 2. 에너지의 전환과 이용 - 02. 에너지는 전환되고 보존돼' 단원을 지도하는 AI 튜터입니다. 교과서 228-231페이지, 자체 제작 교재 87페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅵ_2_03():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅵ. 에너지 전환과 보존 - 2. 에너지의 전환과 이용 - 03. 전기 에너지는 다양하게 이용돼' 단원을 지도하는 AI 튜터입니다. 교과서 232-233페이지, 자체 제작 교재 88페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

def prompt_Ⅵ_2_04():
    return (
        "당신은 중학교 3학년 과학 교과 과정 중 'Ⅵ. 에너지 전환과 보존 - 2. 에너지의 전환과 이용 - 04. 전기 기구는 전기 에너지를 소비해' 단원을 지도하는 AI 튜터입니다. 교과서 234-237페이지, 자체 제작 교재 89-90페이지 내용입니다."
        "답할 수 없는 정보(시험 범위, 시험 날짜 등)에 대해선 선생님께 문의하도록 안내하세요."
    )

# ===== 소단원별 프롬프트 매핑 =====
prompt_map = {
    ("Ⅳ", "1", "01"): prompt_Ⅳ_1_01,
    ("Ⅳ", "1", "02"): prompt_Ⅳ_1_02,
    ("Ⅳ", "1", "03"): prompt_Ⅳ_1_03,
    ("Ⅳ", "1", "04"): prompt_Ⅳ_1_04,
    ("Ⅳ", "2", "01"): prompt_Ⅳ_2_01,
    ("Ⅳ", "2", "02"): prompt_Ⅳ_2_02,
    ("Ⅳ", "2", "03"): prompt_Ⅳ_2_03,
    ("Ⅳ", "2", "04"): prompt_Ⅳ_2_04,
    ("Ⅴ", "1", "01"): prompt_Ⅴ_1_01,
    ("Ⅴ", "1", "02"): prompt_Ⅴ_1_02,
    ("Ⅴ", "1", "03"): prompt_Ⅴ_1_03,
    ("Ⅴ", "1", "04"): prompt_Ⅴ_1_04,
    ("Ⅴ", "1", "05"): prompt_Ⅴ_1_05,
    ("Ⅴ", "2", "01"): prompt_Ⅴ_2_01,
    ("Ⅴ", "2", "02"): prompt_Ⅴ_2_02,
    ("Ⅴ", "2", "03"): prompt_Ⅴ_2_03,
    ("Ⅵ", "1", "01"): prompt_Ⅵ_1_01,
    ("Ⅵ", "1", "02"): prompt_Ⅵ_1_02,
    ("Ⅵ", "2", "01"): prompt_Ⅵ_2_01,
    ("Ⅵ", "2", "02"): prompt_Ⅵ_2_02,
    ("Ⅵ", "2", "03"): prompt_Ⅵ_2_03,
    ("Ⅵ", "2", "04"): prompt_Ⅵ_2_04,
}

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
                        lines = clean_text.strip().splitlines()
                        for line in lines:
                            line = line.strip()
                            # 이미지 링크가 문장 중간에 있어도 추출
                            img_links = re.findall(r"(https?://\S+\.(?:png|jpg|jpeg))", line)
                            for link in img_links:
                                st.image(link)
                                line = line.replace(link, "").strip()
                            if line:
                                st.write(f"**과학 도우미:** {line}")

    input_key = f"user_input_{key_prefix}"
    loading_key = f"loading_{key_prefix}"
    if loading_key not in st.session_state:
        st.session_state[loading_key] = False

        placeholder = st.empty()

        if not st.session_state[loading_key]:
            with placeholder.container():
                user_input = st.text_area("입력: ", value="", key=f"textarea_{key_prefix}_{len(messages)}")
                if st.button("전송", key=f"send_{key_prefix}_{len(messages)}") and user_input.strip():
                    st.session_state[loading_key] = True
                    st.session_state[input_key] = user_input
                    placeholder.empty()
                    st.rerun()
        else:
            st.markdown("<br><i>✏️ 과학 도우미가 답변을 생성 중입니다...</i>", unsafe_allow_html=True)

    if st.session_state[loading_key]:
        user_input = st.session_state.get(input_key, "").strip()
        unit_key = unit.split('.')[0].strip()
        subunit_key = subunit.split('.')[0].strip()
        topic_key = topic.split('.')[0].strip()

        system_prompt = prompt_map.get(
            (unit_key, subunit_key, topic_key),
            lambda: "과학 개념을 설명하는 AI입니다."
        )()

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
