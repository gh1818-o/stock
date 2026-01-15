# app.py
# =========================================================
# DART · DCF Valuation (B2)  —  KRX(pykrx) + DART 중심 리빌드 (UI/UX + 성능 보강)
# - Sidebar 입력창 가독성/톤 완전 통일 (placeholder/입력값/라벨/셀렉트)
# - Sidebar 전체 color 강제 덮어쓰기 제거 (input text/placeholder 깨짐 방지)
# - Peer EV/EBITDA: corp master 반복 로드 병목 제거 (한 번만 로드해서 매핑)
# - 예외/결측 처리 메시지 개선
#
# 필요 패키지:
#   pip install streamlit pandas numpy requests pykrx altair
# =========================================================
import re
import time
import OpenDartReader
import FinanceDataReader as fdr
import streamlit as st
import pandas as pd
import numpy as np
import requests
import zipfile
import io
import xml.etree.ElementTree as ET
import altair as alt
from datetime import datetime, timedelta

from pykrx import stock

# =========================================================
# 0) Page Config
# =========================================================
st.set_page_config(page_title="Valuation", layout="wide")

# =========================================================
# 0-1) CSS (밝은 톤 + 입력 가독성 개선)
# =========================================================
FIN_CSS = """
<style>
/* =========================
   Global typography/layout
========================= */
html, body, [class*="css"]{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR",
               "Apple SD Gothic Neo", "Helvetica Neue", Arial, "Malgun Gothic", sans-serif;
}

.block-container{
  padding-top: 2.2rem !important;
  padding-bottom: 1.6rem !important;
  max-width: 1750px;
}

/* =========================
   Background (LIGHT)
========================= */
.stApp{
  background:
    radial-gradient(1100px 520px at 10% 6%, rgba(59,130,246,0.10), transparent 62%),
    radial-gradient(1000px 520px at 90% 18%, rgba(147,51,234,0.08), transparent 58%),
    radial-gradient(900px 520px at 30% 92%, rgba(16,185,129,0.08), transparent 62%),
    linear-gradient(180deg, #f6f8fc 0%, #eef2f7 100%);
  color: #111827;
}

/* =========================
   Sidebar shell (LIGHT)
========================= */
section[data-testid="stSidebar"]{
  min-width: 380px !important;
  width: 380px !important;
  background: #ffffff !important;
  border-right: 1px solid rgba(15,23,42,0.10);
}

section[data-testid="stSidebar"] .block-container{
  padding-top: 1.0rem !important;
  padding-bottom: 1.0rem !important;
}

/* Sidebar headings/markdown */
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4{
  color: #0f172a !important;
  letter-spacing: -0.3px;
}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] li,
section[data-testid="stSidebar"] span{
  color: rgba(15,23,42,0.72) !important;
}

/* Labels */
label{
  color: rgba(15,23,42,0.72) !important;
  font-weight: 700 !important;
}

/* Caption */
.stCaption{
  color: rgba(15,23,42,0.60) !important;
  font-weight: 520 !important;
}

/* =========================
   Inputs (Unified - LIGHT)  ✅ FIX
   - "입력칸" 느낌 강화 (선명한 테두리 + 필드 배경)
   - 너무 긴 길이 해결: main 영역에서 max-width 제한
   - number_input의 -/+ 스텝 버튼 숨김
========================= */

/* ✅ 1) 메인 영역에서만 입력칸 길이 제한 (사이드바는 그대로) */
section.main div[data-testid="stTextInput"],
section.main div[data-testid="stNumberInput"],
section.main div[data-testid="stSelectbox"]{
  max-width: 480px !important;     /* <- 더 짧게/길게: 480~700 사이로 조절 */
}

/* ✅ 2) number_input의 -/+ 버튼 숨김 (바 느낌 주범) */
section.main div[data-testid="stNumberInput"] button{
  display: none !important;
}
section.main div[data-testid="stNumberInput"] [data-baseweb="button"]{
  display: none !important;
}

/* ✅ 3) wrapper(바탕)도 '필드'처럼 보이게: 테두리/배경 */
div[data-testid="stNumberInput"] div[data-baseweb="input"] > div,
div[data-testid="stTextInput"]   div[data-baseweb="input"] > div{
  background: linear-gradient(
    135deg,
    rgba(255,255,255,0.92) 0%,
    rgba(248,249,255,0.92) 55%,
    rgba(255,255,255,0.90) 100%
  ) !important;

  border: 2px solid rgba(30,41,59,0.22) !important;   /* ✅ 테두리 더 선명 */
  border-radius: 12px !important;
  box-shadow:
    0 1px 0 rgba(255,255,255,0.75) inset,
    0 10px 22px rgba(2,6,23,0.06) !important;          /* ✅ 필드처럼 */
}

/* ✅ 4) 실제 input 텍스트 영역 */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input{
  background: transparent !important;   /* wrapper가 배경 담당 */
  color: rgba(15,23,42,0.92) !important;
  border: 0 !important;
  font-weight: 800 !important;
  padding: 0.46rem 0.70rem !important;  /* ✅ 입력칸 느낌 */
  box-shadow: none !important;
}

/* Password input (DART API 키) */
div[data-testid="stTextInput"] input[type="password"]{
  background: transparent !important;
  color: rgba(15,23,42,0.92) !important;
}

/* Placeholder */
div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stNumberInput"] input::placeholder{
  color: rgba(71,85,105,0.70) !important;
  font-weight: 700 !important;
}

/* Focus (보라 포커스: 배경 블루/보라랑 잘 맞음) */
div[data-testid="stNumberInput"] div[data-baseweb="input"] > div:focus-within,
div[data-testid="stTextInput"]   div[data-baseweb="input"] > div:focus-within{
  border: 2px solid rgba(139,92,246,0.92) !important;
  box-shadow: 0 0 0 4px rgba(139,92,246,0.14) !important;
}

/* Disabled */
div[data-testid="stTextInput"] input:disabled,
div[data-testid="stNumberInput"] input:disabled{
  color: rgba(15,23,42,0.45) !important;
}

/* Manual shares input (발행주식수 수동입력) - 기존 유지 */
input[aria-label^="발행주식수(주) — 직접 입력하면"]{
  background-color: rgba(239,246,255,0.95) !important;
  border: 2px solid rgba(37,99,235,0.95) !important;
  border-radius: 14px !important;
  padding: 0.32rem 0.60rem !important;
  font-weight: 900 !important;
  box-shadow: 0 0 0 4px rgba(37,99,235,0.10) !important;
}

/* Selectbox (BaseWeb) */
div[data-baseweb="select"] > div{
  background: linear-gradient(
    135deg,
    rgba(255,255,255,0.92) 0%,
    rgba(248,249,255,0.92) 55%,
    rgba(255,255,255,0.90) 100%
  ) !important;

  border: 2px solid rgba(30,41,59,0.22) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
}
div[data-baseweb="select"] > div:focus-within{
  border: 2px solid rgba(139,92,246,0.92) !important;
  box-shadow: 0 0 0 4px rgba(139,92,246,0.14) !important;
}
div[data-baseweb="select"] *{
  color: rgba(15,23,42,0.90) !important;
  font-weight: 800 !important;
}


/* =========================
   Buttons (clean, visible on light)
========================= */
div.stButton > button{
  border-radius: 14px !important;
  height: 46px !important;

  background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
  border: none !important;

  color: #ffffff !important;       /* ✅ 텍스트 완전 흰색 */
  font-weight: 950 !important;     /* ✅ 더 선명하게 */
  font-size: 15px !important;      /* ✅ 글씨 키움 */
  letter-spacing: -0.2px !important;

  box-shadow: 0 10px 24px rgba(29,78,216,0.35) !important;
}

/* 버튼 내부의 span/svg까지 전부 흰색 강제 */
div.stButton > button *{
  color: #ffffff !important;
  fill: #ffffff !important;
}

div.stButton > button:hover{
  filter: brightness(1.08) !important;
  transform: translateY(-1px);
}

/* =========================
   Cards / tables (LIGHT)
========================= */
.header-wrap{ margin-top: 0.2rem; margin-bottom: 0.8rem; }
.header-card{
  border: 1px solid rgba(15,23,42,0.10);
  border-radius: 22px;
  padding: 18px 20px;
  background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(248,250,252,0.92));
  box-shadow: 0 14px 30px rgba(2,6,23,0.08);
}
.header-title{ font-size: 26px; font-weight: 950; letter-spacing: -0.6px; margin: 0; line-height: 1.15; color:#0f172a; }
.header-sub{ margin-top: 8px; color: rgba(15,23,42,0.62); font-size: 13px; line-height: 1.55; }

.section-title{
  font-size: 18px;
  font-weight: 950;
  letter-spacing: -0.35px;
  margin: 14px 0 10px 0;
  color: #0f172a;
}
.hr{ height: 1px; background: rgba(15,23,42,0.10); margin: 16px 0; }

.card{
  border: 1px solid rgba(15,23,42,0.10);
  border-radius: 16px;
  padding: 14px 16px;
  background: rgba(255,255,255,0.92);
  box-shadow: 0 14px 24px rgba(2,6,23,0.06);
}
.card-soft{
  border: 1px solid rgba(15,23,42,0.08);
  border-radius: 16px;
  padding: 12px 14px;
  background: rgba(248,250,252,0.92);
  box-shadow: 0 12px 20px rgba(2,6,23,0.05);
}

.kpi-card{
  border: 1px solid rgba(15,23,42,0.10);
  border-radius: 16px;
  padding: 12px 14px;
  background: rgba(255,255,255,0.92);
  box-shadow: 0 14px 24px rgba(2,6,23,0.06);
  min-height: 112px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.kpi-label{ color: rgba(15,23,42,0.62); font-size: 12px; font-weight: 800; line-height: 1.25; }
.kpi-value{ font-size: 22px; font-weight: 950; margin-top: 6px; letter-spacing: -0.2px; color:#0f172a; line-height: 1.15; }
.kpi-sub{ color: rgba(15,23,42,0.55); font-size: 12px; margin-top: 6px; min-height: 16px; line-height: 1.25; }

/* Data tables: header bold */
div[data-testid="stDataFrame"] thead tr th,
div[data-testid="stDataEditor"] thead tr th{
  font-weight: 900 !important;
}


.comment-box{
  border: 1px solid rgba(15,23,42,0.10);
  border-radius: 16px;
  padding: 14px 16px;
  background: rgba(255,255,255,0.92);
  box-shadow: 0 14px 24px rgba(2,6,23,0.06);
}
.comment-title{
  font-size: 14px;
  font-weight: 950;
  letter-spacing: -0.2px;
  margin-bottom: 8px;
  color:#0f172a;
}

/* badges */
.badge{
  display:inline-block;
  padding: 3px 9px;
  border-radius: 999px;
  border: 1px solid rgba(15,23,42,0.12);
  background: rgba(15,23,42,0.04);
  font-size: 12px;
  margin-right: 6px;
  color:#0f172a;
  font-weight: 800;
}
.badge-warn{ background: rgba(245,158,11,0.12); border-color: rgba(245,158,11,0.32); }
.badge-info{ background: rgba(59,130,246,0.10); border-color: rgba(59,130,246,0.28); }
.badge-ok{ background: rgba(16,185,129,0.10); border-color: rgba(16,185,129,0.28); }
.badge-note{ background: rgba(147,51,234,0.10); border-color: rgba(147,51,234,0.28); }

/* dataframe container */
[data-testid="stDataFrame"]{
  border: 1px solid rgba(15,23,42,0.10);
  border-radius: 14px;
  overflow: hidden;
}
</style>
"""
st.markdown(FIN_CSS, unsafe_allow_html=True)


# =========================================================
# 1) Constants / Industry lens
# =========================================================
DART_BASE = "https://opendart.fss.or.kr/api"

INDUSTRY_TAGS = [
    "자동/미지정",
    "조선", "해운",
    "반도체", "2차전지",
    "정유/화학", "철강/소재",
    "건설", "자동차",
    "IT서비스", "통신",
    "게임/엔터", "방산",
    "전력/유틸리티",
    "은행", "증권", "보험",
    "유통/소비",
    "제약/바이오",
    "기타"
]


# =========================================================
# 1-A) Peer presets (업종별 대표 피어 "이름" 리스트)
# - 종목코드는 DART corp master에서 자동으로 찾아 표에 출력
# - 각 업종 최소 20개 이상(여유분 포함)
# =========================================================
PEER_NAMES_BY_TAG: dict[str, list[str]] = {
    "조선": [
        "HD한국조선해양", "HD현대중공업", "HD현대미포", "한화오션", "삼성중공업", "HJ중공업",
        "현대힘스", "세진중공업", "오리엔탈정공", "삼강엠앤티", "한국카본", "동성화인텍",
        "성광벤드", "태웅", "하이록코리아", "현대글로비스", "STX엔진", "HSD엔진",
        "대창솔루션", "케이에스피", "태광", "삼일씨엔에스", "한라IMS", "한텍"
    ],
    "해운": [
        "HMM", "팬오션", "대한해운", "KSS해운", "흥아해운", "세방", "세방전지",
        "인터지스", "KCTC", "동방", "한진", "대한항공", "아시아나항공",
        "진에어", "제주항공", "티웨이항공", "에어부산", "현대글로비스",
        "CJ대한통운", "롯데글로벌로지스", "한진칼", "한익스프레스", "태웅로직스", "토탈소프트"
    ],
    "반도체": [
        "삼성전자", "SK하이닉스", "DB하이텍", "한미반도체", "원익IPS", "주성엔지니어링",
        "유진테크", "테스", "피에스케이", "케이씨텍", "이오테크닉스", "리노공업",
        "ISC", "네패스", "하나마이크론", "SFA반도체", "동진쎄미켐", "솔브레인",
        "심텍", "코미코", "원익QnC", "에프에스티", "디아이", "라온테크"
    ],
    "2차전지": [
        "LG에너지솔루션", "삼성SDI", "SK이노베이션", "포스코퓨처엠", "에코프로비엠", "엘앤에프",
        "에코프로", "코스모신소재", "천보", "대주전자재료", "후성", "일진머티리얼즈",
        "솔루스첨단소재", "SKC", "롯데에너지머티리얼즈", "상신이디피", "피엔티", "나노신소재",
        "원익머트리얼즈", "케이엔더블유", "성우하이텍", "서진시스템", "동화기업", "코스모화학"
    ],
    "정유/화학": [
        "S-Oil", "SK이노베이션", "GS", "현대오일뱅크", "LG화학", "롯데케미칼",
        "한화솔루션", "금호석유", "DL", "효성화학", "OCI", "SKC",
        "롯데정밀화학", "KPX케미칼", "애경케미칼", "대한유화", "태광산업", "이수화학",
        "SK디스커버리", "코오롱인더", "국도화학", "동성케미컬", "케이피에스", "윌비스"
    ],
    "철강/소재": [
        "POSCO홀딩스", "현대제철", "동국제강", "세아제강", "세아베스틸지주", "고려아연",
        "풍산", "KG스틸", "동국S&C", "대한제강", "한국철강", "문배철강",
        "휴스틸", "넥스틸", "알루코", "남선알미늄", "포스코스틸리온", "포스코인터내셔널",
        "TCC스틸", "조일알미늄", "서원", "고려특수선재", "동양철관", "삼현철강"
    ],
    "건설": [
        "현대건설", "GS건설", "DL이앤씨", "대우건설", "HDC현대산업개발", "삼성물산",
        "코오롱글로벌", "한신공영", "금호건설", "계룡건설", "태영건설", "동부건설",
        "남광토건", "서희건설", "KCC건설", "동원개발", "진흥기업", "신세계건설",
        "삼부토건", "일성건설", "HJ중공업", "한라", "특수건설", "우원개발"
    ],
    "자동차": [
        "현대차", "기아", "현대모비스", "현대위아", "HL만도", "한온시스템",
        "에스엘", "현대공업", "평화산업", "화신", "모트렉스", "서연",
        "서연이화", "세방전지", "SNT모티브", "SNT다이내믹스", "성우하이텍", "명신산업",
        "대원강업", "체시스", "디아이씨", "일진하이솔루스", "우리산업", "네오오토"
    ],
    "IT서비스": [
        "NAVER", "카카오", "삼성SDS", "더존비즈온", "NHN", "LG씨엔에스",
        "SK", "KTis", "KTcs", "포스코DX", "롯데이노베이트", "다우기술",
        "솔트룩스", "코난테크놀로지", "이스트소프트", "핸디소프트", "한글과컴퓨터", "안랩",
        "지란지교시큐리티", "SGA솔루션즈", "케이사인", "라온시큐어", "드림시큐리티", "알서포트"
    ],
    "통신": [
        "SK텔레콤", "KT", "LG유플러스", "쏠리드", "다산네트웍스", "KMW", "RFHIC",
        "이노와이어리스", "텔코웨어", "유비쿼스", "우리넷", "오이솔루션", "케이엠더블유",
        "에이스테크", "CS", "서진시스템", "대한광통신", "머큐리", "드림어스컴퍼니",
        "인스코비", "SK스퀘어", "아이크래프트", "빛샘전자", "유엔젤"
    ],
    "게임/엔터": [
        "엔씨소프트", "넷마블", "크래프톤", "카카오게임즈", "위메이드", "펄어비스",
        "컴투스", "데브시스터즈", "웹젠", "더블유게임즈", "네오위즈", "엠게임",
        "하이브", "에스엠", "JYP Ent.", "YG엔터테인먼트", "CJ ENM", "스튜디오드래곤",
        "키다리스튜디오", "디앤씨미디어", "쇼박스", "NEW", "SBS", "KBS미디어"
    ],
    "방산": [
        "한화에어로스페이스", "한국항공우주", "LIG넥스원", "현대로템", "한화시스템", "풍산",
        "SNT모티브", "SNT다이내믹스", "휴니드", "퍼스텍", "빅텍", "스페코",
        "아이쓰리시스템", "한일단조", "기산텔레콤", "한컴라이프케어", "코츠테크놀로지", "이엠코리아",
        "대양전기공업", "삼영이엔씨", "제노코", "켄코아에어로스페이스", "아스트", "쎄트렉아이"
    ],
    "전력/유틸리티": [
        "한국전력", "한국가스공사", "지역난방공사", "두산에너빌리티", "한전KPS", "한전기술",
        "LS ELECTRIC", "HD현대일렉트릭", "효성중공업", "일진전기", "LS", "대한전선",
        "가온전선", "제룡전기", "산일전기", "비츠로테크", "비츠로셀", "대성에너지",
        "삼천리", "서울가스", "대성홀딩스", "E1", "SK가스", "한국전력기술"
    ],
    "은행": [
        "KB금융", "신한지주", "하나금융지주", "우리금융지주", "기업은행", "BNK금융지주",
        "JB금융지주", "DGB금융지주", "카카오뱅크", "제주은행", "푸른저축은행", "상상인저축은행",
        "한국캐피탈", "JB우리캐피탈", "BNK캐피탈", "우리금융캐피탈", "롯데지주", "삼성카드",
        "롯데지주", "메리츠금융지주", "한국금융지주", "미래에셋증권", "NH투자증권", "키움증권"
    ],
    "증권": [
        "미래에셋증권", "NH투자증권", "한국금융지주", "삼성증권", "키움증권", "대신증권",
        "유안타증권", "DB금융투자", "한화투자증권", "신영증권", "유진투자증권", "LS증권",
        "SK증권", "현대차증권", "부국증권", "한양증권", "메리츠금융지주", "카카오페이",
        "토스", "다올투자증권", "교보증권", "유화증권", "상상인증권", "리딩투자증권"
    ],
    "보험": [
        "삼성생명", "삼성화재", "DB손해보험", "현대해상", "한화생명", "한화손해보험",
        "미래에셋생명", "코리안리", "동양생명", "흥국화재", "메리츠화재", "롯데손해보험",
        "AIA생명", "푸본현대생명", "KB손해보험", "NH농협생명", "NH농협손해보험", "교보생명",
        "카카오페이", "삼성카드", "현대해상", "DB손해보험", "한화생명", "코리안리"
    ],
    "유통/소비": [
        "이마트", "롯데쇼핑", "현대백화점", "BGF리테일", "GS리테일", "신세계",
        "CJ", "CJ제일제당", "오리온", "롯데웰푸드", "농심", "삼양식품",
        "빙그레", "하이트진로", "롯데칠성", "아모레퍼시픽", "LG생활건강", "F&F",
        "휠라홀딩스", "영원무역", "한섬", "LF", "코웨이", "쿠쿠홀딩스"
    ],
    "제약/바이오": [
        "삼성바이오로직스", "셀트리온", "SK바이오팜", "SK바이오사이언스", "유한양행", "한미약품",
        "녹십자", "종근당", "대웅제약", "보령", "JW중외제약", "일동제약",
        "동아에스티", "제일약품", "한올바이오파마", "휴젤", "메디톡스", "씨젠",
        "알테오젠", "레고켐바이오", "에스티팜", "바이오니아", "HK이노엔", "대원제약"
    ],
}

def _normalize_name(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())

def resolve_stock_code_by_name(master_df: pd.DataFrame, corp_name: str) -> str | None:
    """
    corp_name -> stock_code(6자리) 를 DART corp master에서 최대한 안전하게 찾습니다.
    """
    if master_df is None or master_df.empty:
        return None
    nm = (corp_name or "").strip()
    if not nm:
        return None

    # 1) 완전일치 우선
    sub = master_df[master_df["corp_name"] == nm].copy()

    # 2) 공백 제거 후 contains
    if sub.empty:
        key = _normalize_name(nm)
        tmp = master_df.copy()
        tmp["_nm"] = tmp["corp_name"].astype(str).map(_normalize_name)
        sub = tmp[tmp["_nm"].str.contains(key, na=False)].copy()

    if sub.empty:
        return None

    # stock_code가 있는 것 우선
    sub["stock_code"] = sub["stock_code"].astype(str).str.strip()
    sub2 = sub[sub["stock_code"].str.fullmatch(r"\d{6}", na=False)]
    if not sub2.empty:
        return _ticker6(sub2.iloc[0]["stock_code"])

    # 없으면 None
    return None

def infer_tag_from_name(corp_name: str) -> str | None:
    """
    선택한 회사명이 어떤 업종 피어 리스트 안에 있으면 그 업종을 자동 추정.
    """
    nm = (corp_name or "").strip()
    if not nm:
        return None
    for tag, names in PEER_NAMES_BY_TAG.items():
        if nm in names:
            return tag
    return None

def build_peer_table(industry_tag: str, master_df: pd.DataFrame, target_ticker6: str | None = None, max_rows: int = 20) -> pd.DataFrame:
    names = PEER_NAMES_BY_TAG.get(industry_tag, [])
    if not names:
        return pd.DataFrame()

    target = _ticker6(target_ticker6) if target_ticker6 else None

    # 타깃 시총
    target_mkt = None
    if target:
        try:
            target_mkt = float(krx_market_cap_latest(target).get("mktcap", np.nan))
        except Exception:
            target_mkt = None
        if target_mkt is not None and (not np.isfinite(target_mkt) or target_mkt <= 0):
            target_mkt = None

    rows = []
    for nm in names:
        tk = resolve_stock_code_by_name(master_df, nm)
        if not tk:
            continue
        if target and tk == target:
            continue
        try:
            m = float(krx_market_cap_latest(tk).get("mktcap", np.nan))
        except Exception:
            m = np.nan
        ratio = (m / target_mkt) if (target_mkt is not None and np.isfinite(m)) else np.nan
        rows.append({"회사": nm, "종목코드": tk, "_mktcap": m, "_ratio": ratio})

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # 타깃 시총이 있으면 '비슷한 규모(0.3x~3.0x)' 우선 노출
    if target_mkt is not None:
        df2 = df.copy()
        df2["_dist"] = (np.log(df2["_ratio"].clip(lower=1e-9))).abs()
        df_sim = df2[(df2["_ratio"] >= 0.3) & (df2["_ratio"] <= 3.0)].sort_values("_dist")
        df = df_sim if len(df_sim) >= 5 else df2.sort_values("_dist")

    df["시총(조원)"] = df["_mktcap"].apply(lambda x: "-" if (x is None or not np.isfinite(x)) else f"{x/1e12:,.2f}")
    df["타깃대비"] = df["_ratio"].apply(lambda x: "-" if (x is None or not np.isfinite(x)) else f"{x:,.2f}x")
    out = df[["회사", "종목코드", "시총(조원)", "타깃대비"]].head(max_rows).reset_index(drop=True)
    return out




# =========================================================
# 2) Utils
# =========================================================
def is_trillion_mode(unit: str) -> bool:
    return unit is not None and ("조원" in unit)

def corp_cls_to_kor(code: str) -> str:
    return {"Y": "유가(KOSPI)", "K": "코스닥(KOSDAQ)", "N": "코넥스(KONEX)", "E": "기타"}.get(code, code or "")

def clean_empty_rows_cols(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.replace("", np.nan)
    out = out.dropna(axis=0, how="all").dropna(axis=1, how="all")
    return out

def add_year_term_index(df: pd.DataFrame, year_to_term: dict) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    view = df.copy()
    new_idx = []
    for y in view.index.tolist():
        try:
            term = year_to_term.get(int(y), "")
        except Exception:
            term = ""
        new_idx.append(f"{y} ({term})" if term else f"{y}")
    view.index = new_idx
    view.index.name = "연도(기수)"
    return view

def df_height(df: pd.DataFrame, max_rows: int = 60, row_h: int = 34, header_h: int = 38, pad: int = 10) -> int:
    if df is None or df.empty:
        return header_h + pad
    n = min(len(df), max_rows)
    return header_h + n * row_h + pad

def safe_div(a, b):
    if a is None or b is None:
        return None
    try:
        b = float(b)
        if b == 0:
            return None
        return float(a) / b
    except Exception:
        return None

def last_value(series: pd.Series):
    if series is None:
        return None
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return None
    return float(s.iloc[0])

def prev_value(series: pd.Series):
    if series is None:
        return None
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 2:
        return None
    return float(s.iloc[1])

def pct_change(curr: float, prev: float):
    if curr is None or prev is None:
        return None
    if prev == 0 or (isinstance(prev, float) and np.isnan(prev)):
        return None
    return curr / prev - 1

def trend_slope(series: pd.Series):
    if series is None:
        return None
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 3:
        return None
    s2 = s.iloc[::-1].values.astype(float)
    x = np.arange(len(s2), dtype=float)
    return float(np.polyfit(x, s2, 1)[0])

def badge_html(text: str, kind: str = "info"):
    cls = "badge"
    if kind == "warn":
        cls += " badge-warn"
    elif kind == "ok":
        cls += " badge-ok"
    elif kind == "note":
        cls += " badge-note"
    else:
        cls += " badge-info"
    return f"<span class='{cls}'>{text}</span>"

def fmt_money_value(x: float, unit: str) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    if is_trillion_mode(unit):
        return f"{x/1_000_000_000_000:,.3f}"
    return f"{x:,.0f}"

def _now_kst():
    # 서버 로컬타임/UTC 차이로 KRX 휴장일 처리 깨지는 경우가 있어 KST 기준 문자열을 사용
    return datetime.utcnow() + timedelta(hours=9)

def today_krx_str():
    return _now_kst().strftime("%Y%m%d")

def ymd(dt: datetime):
    return dt.strftime("%Y%m%d")

# =========================================================
# 3) Charts (Altair)
# =========================================================
COLOR = {
    "rev": "#60a5fa",
    "op":  "#34d399",
    "ni":  "#c084fc",
    "margin": "#fbbf24",
    "ratio1": "#38bdf8",
    "ratio2": "#fb7185",
    "ratio3": "#94a3b8",
    "price": "#60a5fa",
}

def alt_line_chart(series: pd.Series, unit: str, is_ratio: bool = False, height: int = 220, color: str = "#60a5fa"):
    if series is None:
        return None
    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().empty:
        return None

    years = list(reversed(s.index.tolist()))
    vals = list(reversed(s.values.tolist()))

    if not is_ratio and is_trillion_mode(unit):
        vals = [v/1_000_000_000_000 if pd.notna(v) else np.nan for v in vals]

    df = pd.DataFrame({"Year": years, "Value": vals})
    try:
        df["Year"] = df["Year"].astype(int)
    except Exception:
        pass

    if is_ratio:
        y_fmt = ".1%"
        tip_fmt = ".2%"
    else:
        y_fmt = ",.3f" if is_trillion_mode(unit) else ",.0f"
        tip_fmt = ",.3f" if is_trillion_mode(unit) else ",.0f"

    chart = (
        alt.Chart(df)
        .mark_line(point=alt.OverlayMarkDef(filled=True, size=45), color=color)
        .encode(
            x=alt.X("Year:O", title=None),
            y=alt.Y("Value:Q", title=None, axis=alt.Axis(format=y_fmt)),
            tooltip=[alt.Tooltip("Year:O", title="연도"),
                     alt.Tooltip("Value:Q", title="값", format=tip_fmt)],
        )
        .properties(height=height)
    )
    return chart

def alt_time_series(df: pd.DataFrame, x: str, y: str, title: str, height: int = 260, fmt: str = ",.0f", color="#60a5fa"):
    if df is None or df.empty:
        return None
    chart = (
        alt.Chart(df)
        .mark_line(color=color)
        .encode(
            x=alt.X(f"{x}:T", title=None),
            y=alt.Y(f"{y}:Q", title=None, axis=alt.Axis(format=fmt)),
            tooltip=[alt.Tooltip(f"{x}:T", title="일자"), alt.Tooltip(f"{y}:Q", title=title, format=fmt)],
        )
        .properties(height=height)
    )
    return chart

def render_plain_chart(title: str, chart):
    st.markdown(f"**{title}**")
    if chart is None:
        st.info("데이터 없음")
        return
    st.altair_chart(chart, use_container_width=True)

# =========================================================
# 4) DART API (corp master + company + FS)
# =========================================================
@st.cache_data(show_spinner=False, ttl=60*60*24)
def load_corp_master(crtfc_key: str) -> pd.DataFrame:
    url = f"{DART_BASE}/corpCode.xml"
    r = requests.get(url, params={"crtfc_key": crtfc_key}, timeout=30)
    r.raise_for_status()

    z = zipfile.ZipFile(io.BytesIO(r.content))
    xml_name = [n for n in z.namelist() if n.lower().endswith(".xml")][0]
    xml_bytes = z.read(xml_name)

    root = ET.fromstring(xml_bytes)
    rows = []
    for item in root.findall("list"):
        corp_code = (item.findtext("corp_code") or "").strip()
        corp_name = (item.findtext("corp_name") or "").strip()
        stock_code = (item.findtext("stock_code") or "").strip()
        modify_date = (item.findtext("modify_date") or "").strip()
        rows.append([corp_code, corp_name, stock_code, modify_date])

    return pd.DataFrame(rows, columns=["corp_code", "corp_name", "stock_code", "modify_date"])

@st.cache_data(show_spinner=False, ttl=60*60)
def dart_company_info(crtfc_key: str, corp_code: str) -> dict:
    url = f"{DART_BASE}/company.json"
    r = requests.get(url, params={"crtfc_key": crtfc_key, "corp_code": corp_code}, timeout=20)
    data = r.json()
    if data.get("status") != "000":
        raise ValueError(data.get("message"))
    return data



@st.cache_data(show_spinner=False, ttl=60*60)
def dart_major_accounts(crtfc_key: str, corp_code: str, bsns_year: str, reprt_code: str, fs_div: str) -> pd.DataFrame:
    url = f"{DART_BASE}/fnlttSinglAcnt.json"
    params = {
        "crtfc_key": crtfc_key,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div
    }
    r = requests.get(url, params=params, timeout=30)
    data = r.json()
    if data.get("status") != "000":
        raise ValueError(data.get("message"))
    return pd.DataFrame(data.get("list", []))

@st.cache_data(show_spinner=False, ttl=60*60)
def dart_all_accounts(crtfc_key: str, corp_code: str, bsns_year: str, reprt_code: str, fs_div: str) -> pd.DataFrame:
    url = f"{DART_BASE}/fnlttSinglAcntAll.json"
    params = {
        "crtfc_key": crtfc_key,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div
    }
    r = requests.get(url, params=params, timeout=40)
    data = r.json()
    if data.get("status") != "000":
        raise ValueError(data.get("message"))
    return pd.DataFrame(data.get("list", []))


@st.cache_data(show_spinner=False, ttl=60*60)
def fetch_wc_bs_history(crtfc_key: str, corp_code: str, end_year: int, n_years: int, reprt_code: str, fs_div: str) -> pd.DataFrame:
    years = list(range(end_year, end_year - n_years, -1))
    rows = []
    for y in years:
        all_df = dart_all_accounts(crtfc_key, corp_code, str(y), reprt_code, fs_div)
        if all_df is None or all_df.empty:
            continue

        # DART 응답에 sj_div(재무제표구분)가 있으면 BS만 필터
        df_bs = all_df
        if "sj_div" in all_df.columns:
            df_bs = all_df[all_df["sj_div"].astype(str).str.upper().eq("BS")].copy()
            if df_bs.empty:
                df_bs = all_df  # 혹시 sj_div가 이상하면 전체에서라도 찾기

        ar  = _pick_first_amount(df_bs, ACCOUNT_ALIASES.get("AR", []))
        inv = _pick_first_amount(df_bs, ACCOUNT_ALIASES.get("INV", []))
        ap  = _pick_first_amount(df_bs, ACCOUNT_ALIASES.get("AP", []))

        rows.append({"연도": y, "AR": ar, "INV": inv, "AP": ap})

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).set_index("연도").sort_index(ascending=False)



def find_corp_code(master: pd.DataFrame, mode: str, query: str) -> pd.DataFrame:
    q = (query or "").strip()
    if not q:
        return pd.DataFrame()
    if mode == "종목코드":
        q = "".join([c for c in q if c.isdigit()]).zfill(6)
        return master[master["stock_code"] == q]
    return master[master["corp_name"].str.contains(q, na=False)]

@st.cache_data(show_spinner=False, ttl=60*60)
def fetch_last_n_years_wide(crtfc_key: str, corp_code: str, end_year: int, n_years: int, reprt_code: str, fs_div: str):
    records = []
    year_to_term = {}
    years = list(range(end_year, end_year - n_years, -1))
    for y in years:
        fin = dart_major_accounts(crtfc_key, corp_code, str(y), reprt_code, fs_div)
        if fin is None or fin.empty:
            continue

        if "thstrm_nm" in fin.columns and fin["thstrm_nm"].notna().any():
            year_to_term[y] = str(fin["thstrm_nm"].dropna().iloc[0]).strip()

        for _, r in fin.iterrows():
            acc = (r.get("account_nm") or "").strip()
            amt = r.get("thstrm_amount", None)
            if acc and pd.notna(amt):
                records.append({"연도": y, "계정과목": acc, "금액": str(amt).replace(",", "").strip()})

    if not records:
        return pd.DataFrame(), {}

    df = pd.DataFrame(records)
    df["금액"] = pd.to_numeric(df["금액"], errors="coerce")

    wide = (
        df.pivot_table(index="연도", columns="계정과목", values="금액", aggfunc="first")
          .sort_index(ascending=False)
          .dropna(axis=1, how="all")
    )
    return wide, year_to_term


@st.cache_data(show_spinner=False, ttl=60*60)
def fetch_last_n_years_is_items(crtfc_key: str, corp_code: str, end_year: int, n_years: int, reprt_code: str, fs_div: str):
    years = list(range(end_year, end_year - n_years, -1))
    year_to_term = {}
    rows = []

    # “영업외수익/비용” 추출용 키워드(회사마다 계정명이 달라서 포함검색+합산)
    NONOP_INCOME_KEYS = [
        "영업외수익", "기타수익", "금융수익", "이자수익", "배당금수익",
        "외환차익", "환차익", "파생상품이익", "지분법이익", "관계기업", "처분이익", "평가이익"
    ]
    NONOP_EXPENSE_KEYS = [
        "영업외비용", "기타비용", "금융비용", "이자비용",
        "외환차손", "환차손", "파생상품손실", "지분법손실", "처분손실", "평가손실"
    ]

    def sum_accounts_contains(df: pd.DataFrame, keys: list[str], amount_col="thstrm_amount") -> float | None:
        if df is None or df.empty:
            return None
        tmp = df.copy()
        tmp["account_nm_n"] = tmp["account_nm"].astype(str).map(_norm)

        vals = []
        for k in keys:
            kk = _norm(k)
            hit = tmp[tmp["account_nm_n"].str.contains(kk, na=False)]
            if not hit.empty:
                for v in hit[amount_col].tolist():
                    nv = _to_num(v)
                    if nv is not None:
                        vals.append(nv)
        return float(np.sum(vals)) if vals else None

    for y in years:
        all_df = dart_all_accounts(crtfc_key, corp_code, str(y), reprt_code, fs_div)
        if all_df is None or all_df.empty:
            continue

        # 기수명
        if "thstrm_nm" in all_df.columns and all_df["thstrm_nm"].notna().any():
            year_to_term[y] = str(all_df["thstrm_nm"].dropna().iloc[0]).strip()

        # 기본 IS 라인
        rev = _pick_first_amount(all_df, ["매출액", "영업수익", "수익", "매출", "매출총액"])
        cogs = _pick_first_amount(all_df, ["매출원가", "원가"])
        sga  = _pick_first_amount(all_df, ["판매비와관리비", "판매관리비", "판관비"])
        op   = _pick_first_amount(all_df, ["영업이익", "영업이익(손실)", "영업손익"])
        tax  = _pick_first_amount(all_df, ["법인세비용", "법인세비용(수익)", "법인세"])
        ni   = _pick_first_amount(all_df, ["당기순이익", "당기순이익(손실)"])

        # 매출총이익 (없으면 계산)
        gp = _pick_first_amount(all_df, ["매출총이익"])
        if gp is None and (rev is not None) and (cogs is not None):
            gp = rev - cogs

        # ✅ 여기서 너가 원하는 영업외수익/영업외비용을 만든다(합산)
        nonop_income = sum_accounts_contains(all_df, NONOP_INCOME_KEYS)
        nonop_expense = sum_accounts_contains(all_df, NONOP_EXPENSE_KEYS)

        # 영업외손익(표시용) = 수익-비용 (둘 다 있으면)
        nonop_net = None
        if nonop_income is not None and nonop_expense is not None:
            nonop_net = nonop_income - nonop_expense

        # (보조) 영업외손익이 아예 안 잡힐 때 검증값: NI - OP + TAX
        nonop_net_check = None
        if (ni is not None) and (op is not None) and (tax is not None):
            nonop_net_check = ni - op + tax

        rows.append({
            "연도": y,
            "매출": rev,
            "원가": cogs,
            "매출총이익": gp,
            "판관비": sga,
            "영업이익": op,
            "영업외수익": nonop_income,
            "영업외비용": nonop_expense,
            "영업외손익(수익-비용)": nonop_net,
            "영업외손익(검증)": nonop_net_check,
            "법인세": tax,
            "당기순이익": ni,
        })

    if not rows:
        return pd.DataFrame(), {}

    wide_is = (
        pd.DataFrame(rows)
        .set_index("연도")
        .sort_index(ascending=False)
    )
    return wide_is, year_to_term


@st.cache_data(show_spinner=False, ttl=60*60)
def fetch_last_n_years_is_wide(crtfc_key: str, corp_code: str, end_year: int, n_years: int, reprt_code: str, fs_div: str):
    """
    IS 전용: fnlttSinglAcntAll(전체계정)에서
    매출/원가/매출총이익/판관비/영업이익/영업외/법인세/당기순이익 형태로 재구성
    """
    years = list(range(end_year, end_year - n_years, -1))
    year_to_term = {}
    rows = []

    for y in years:
        all_df = dart_all_accounts(crtfc_key, corp_code, str(y), reprt_code, fs_div)
        if all_df is None or all_df.empty:
            continue

        if "thstrm_nm" in all_df.columns and all_df["thstrm_nm"].notna().any():
            year_to_term[y] = str(all_df["thstrm_nm"].dropna().iloc[0]).strip()

        def pick(alias_key: str):
            return _pick_first_amount(all_df, ACCOUNT_ALIASES.get(alias_key, []))

        rev = pick("REV")
        cogs = pick("COGS")
        sga  = pick("SGA")
        op   = pick("OP")
        ni   = pick("NI")
        tax  = pick("TAX")

        noi = pick("NOI")
        noe = pick("NOE")
        nonop = None
        if (noi is not None) or (noe is not None):
            nonop = (noi or 0.0) - (noe or 0.0)

        gp = None
        if (rev is not None) and (cogs is not None):
            gp = rev - cogs
        elif (op is not None) and (sga is not None):
            # 원가가 없으면 대체: 매출총이익 ≈ 영업이익 + 판관비
            gp = op + sga

        rows.append({
            "연도": y,
            "매출": rev,
            "원가": cogs,
            "매출총이익": gp,
            "판관비": sga,
            "영업이익": op,
            "영업외": nonop,
            "법인세": tax,
            "당기순이익": ni,
        })

    if not rows:
        return pd.DataFrame(), year_to_term

    wide_is = pd.DataFrame(rows).set_index("연도").sort_index(ascending=False)
    return wide_is, year_to_term


# =========================================================
# 5) Account aliases (DART 계정명 대응)
# =========================================================
ACCOUNT_ALIASES = {
    "REV": ["매출액", "영업수익", "수익", "매출", "매출총액"],
    "OP":  ["영업이익", "영업손익", "영업이익(손실)"],
    "NI":  ["당기순이익", "당기순이익(손실)"],
    "ASSET": ["자산총계", "자산 총계"],
    "LIAB":  ["부채총계", "부채 총계"],
    "EQUITY":["자본총계", "자본 총계"],
    "CA": ["유동자산", "유동 자산"],
    "CL": ["유동부채", "유동 부채"],
    "COGS": ["매출원가", "영업비용", "매출원가및판관비"],  # 회사마다 표현 달라서 넓게
    "SGA":  ["판매비와관리비", "판매비및관리비", "판관비"],
    "TAX":  ["법인세비용", "법인세비용(수익)", "법인세"],
    "NOI":  ["영업외수익", "금융수익", "기타수익"],
    "NOE":  ["영업외비용", "금융비용", "기타비용"],

    "NCA":  ["비유동자산", "비유동 자산"],
    "NCL":  ["비유동부채", "비유동 부채"],
    "CAPITAL": ["자본금"],
    
    # 운전자본 회전율용 (회사별 표기 다양해서 넓게)
    "AR": ["매출채권", "매출채권및기타채권", "매출채권 및 기타채권", "받을어음", "미수금", "미수채권"],
    "INV": ["재고자산", "재고", "상품", "제품", "재공품", "원재료"],
    "AP": ["매입채무", "매입채무및기타채무", "매입채무 및 기타채무", "지급어음", "미지급금"],

}

def pick_account_series(wide: pd.DataFrame, candidates: list[str]):
    if wide is None or wide.empty:
        return None, None
    for c in candidates:
        if c in wide.columns:
            return c, wide[c]
    return None, None

def pick_by_alias(wide: pd.DataFrame, key: str):
    return pick_account_series(wide, ACCOUNT_ALIASES.get(key, []))

def prepare_table_display(wide: pd.DataFrame, year_to_term: dict, unit: str) -> pd.DataFrame:
    if wide is None or wide.empty:
        return pd.DataFrame()
    view = add_year_term_index(wide, year_to_term)
    disp = pd.DataFrame(index=view.index)

    if is_trillion_mode(unit):
        view = view / 1_000_000_000_000
        for c in view.columns:
            s = pd.to_numeric(view[c], errors="coerce")
            disp[c] = s.map(lambda v: "" if pd.isna(v) else f"{float(v):,.3f}")
    else:
        for c in view.columns:
            s = pd.to_numeric(view[c], errors="coerce")
            disp[c] = s.map(lambda v: "" if pd.isna(v) else f"{float(v):,.0f}")

    return clean_empty_rows_cols(disp)

# =========================================================
# 6) KRX(pykrx) Market data
# =========================================================
def _ticker6(code: str) -> str:
    return "".join([c for c in (code or "") if c.isdigit()]).zfill(6)

@st.cache_data(show_spinner=False, ttl=60*30)
def krx_price_history(ticker6: str, start: str, end: str) -> pd.DataFrame:
    """
    KRX OHLCV 히스토리.
    end가 휴장일(주말/공휴일)이면 pykrx가 빈 DF를 주는 케이스가 있어,
    마지막 영업일로 자동 롤백해서 데이터를 확보한다.
    """
    t = _ticker6(ticker6)

    # 날짜 문자열 정리
    s = start
    d = end

    # end 롤백하며 시도 (최대 40일)
    for _ in range(40):
        df = stock.get_market_ohlcv_by_date(s, d, t)
        if df is not None and not df.empty:
            out = df.reset_index().rename(columns={"날짜": "Date", "종가": "Close", "거래량": "Volume"})
            out["Date"] = pd.to_datetime(out["Date"])
            out = out[["Date", "Close", "Volume"]].copy()
            out["Close"] = pd.to_numeric(out["Close"], errors="coerce")
            out["Volume"] = pd.to_numeric(out["Volume"], errors="coerce")
            out = out.dropna(subset=["Close"])
            return out

        # 하루 전으로 롤백
        d = ymd(datetime.strptime(d, "%Y%m%d") - timedelta(days=1))

    return pd.DataFrame()


@st.cache_data(show_spinner=False, ttl=60*30)
def krx_market_cap_latest(ticker6: str, on: str | None = None) -> dict:
    """
    KRX 시총/주식수/종가를 조회합니다.
    - 핵심 수정: pykrx가 반환하는 df.index가 int/비정규 문자열인 경우가 있어
      ticker 매칭이 실패(t in df.index False) → 연도말 시총이 전부 fallback 되는 문제가 발생.
    - 해결: df.index를 항상 '6자리 문자열'로 정규화(zfill(6)) 후 매칭.
    """
    t = _ticker6(ticker6)
    d = on or today_krx_str()

    for _ in range(40):  # 휴장/연휴 롤백
        try:
            df = stock.get_market_cap_by_ticker(d)
        except Exception:
            df = None

        if df is not None and not df.empty:
            # ✅ index 정규화 (가장 중요)
            try:
                df = df.copy()
                df.index = df.index.astype(str).str.zfill(6)
            except Exception:
                pass

            if t in df.index:
                row = df.loc[t]

                def _to_float_or_none(x):
                    try:
                        v = float(x)
                        if np.isnan(v) or np.isinf(v):
                            return None
                        return v
                    except Exception:
                        return None

                return {
                    "date": d,
                    "mktcap": _to_float_or_none(row.get("시가총액", np.nan)),
                    "shares": _to_float_or_none(row.get("상장주식수", np.nan)),
                    "close": _to_float_or_none(row.get("종가", np.nan)),
                }

        # 하루 전으로 롤백
        try:
            d = ymd(datetime.strptime(d, "%Y%m%d") - timedelta(days=1))
        except Exception:
            break

    return {"date": None, "mktcap": None, "shares": None, "close": None}


@st.cache_data(show_spinner=False, ttl=60*30)
def krx_nearest_business_day(d: str) -> str:
    """
    pykrx가 제공하는 '가까운 영업일' 함수가 있으면 그걸 쓰고,
    없으면 -1일씩 롤백.
    """
    from datetime import datetime, timedelta
    from pykrx import stock

    d = str(d).strip()
    try:
        if hasattr(stock, "get_nearest_business_day_in_a_week"):
            return stock.get_nearest_business_day_in_a_week(d)
    except Exception:
        pass

    # fallback: 수동 롤백
    cur = d
    for _ in range(40):
        try:
            df = stock.get_market_cap_by_ticker(cur)
            if df is not None and not df.empty:
                return cur
        except Exception:
            pass
        cur = ymd(datetime.strptime(cur, "%Y%m%d") - timedelta(days=1))
    return d


@st.cache_data(show_spinner=False, ttl=60*30)
def krx_market_cap_on(ticker6: str, on: str) -> dict:
    """
    특정일(휴장이면 가장 가까운 영업일) 기준 시총/주식수/종가
    """
    from pykrx import stock
    t = _ticker6(ticker6)
    d = krx_nearest_business_day(on)

    try:
        df = stock.get_market_cap_by_ticker(d)
        if df is not None and (not df.empty) and t in df.index:
            r = df.loc[t]
            return {
                "date": d,
                "mktcap": float(r.get("시가총액", np.nan)),
                "shares": float(r.get("상장주식수", np.nan)),
                "close": float(r.get("종가", np.nan)),
            }
    except Exception:
        pass

    return {"date": None, "mktcap": None, "shares": None, "close": None}


@st.cache_data(show_spinner=False, ttl=60*30)
def krx_year_end_mktcap(ticker6: str, end_year: int, n_years: int) -> pd.DataFrame:
    """
    연도말(해당연도 12/31 근처 마지막 영업일) 시총 시계열
    반환: Year, MktCap, MktCap_date
    """
    t = _ticker6(ticker6)
    years = list(range(int(end_year) - int(n_years) + 1, int(end_year) + 1))
    rows = []

    for y in years:
        d0 = f"{y}1231"
        info = krx_market_cap_on(t, d0)
        rows.append({
            "Year": int(y),
            "MktCap": info.get("mktcap"),
            "MktCap_date": info.get("date"),
        })

    return pd.DataFrame(rows).sort_values("Year", ascending=False).reset_index(drop=True)




@st.cache_data(show_spinner=False, ttl=60*30)
def krx_fundamental_latest(ticker6: str, on: str | None = None) -> dict:
    t = _ticker6(ticker6)
    d = on or today_krx_str()
    for _ in range(40):
        df = stock.get_market_fundamental_by_ticker(d)
        if df is not None and not df.empty and t in df.index:
            r = df.loc[t]
            def _nan_to_none(x):
                try:
                    x = float(x)
                    if np.isnan(x) or np.isinf(x):
                        return None
                    return x
                except Exception:
                    return None
            return {
                "date": d,
                "PER": _nan_to_none(r.get("PER", np.nan)),
                "PBR": _nan_to_none(r.get("PBR", np.nan)),
                "EPS": _nan_to_none(r.get("EPS", np.nan)),
                "BPS": _nan_to_none(r.get("BPS", np.nan)),
                "DIV": _nan_to_none(r.get("DIV", np.nan)),
            }
        d = ymd(datetime.strptime(d, "%Y%m%d") - timedelta(days=1))
    return {"date": None, "PER": None, "PBR": None, "EPS": None, "BPS": None, "DIV": None}


@st.cache_data(show_spinner=False, ttl=60*30)
def krx_market_cap_universe(on: str | None = None) -> pd.DataFrame:
    """
    KRX 전체 종목(가능하면 KOSPI+KOSDAQ) 시총 유니버스
    반환: index=ticker6, columns에 종목명/시가총액/상장주식수 등 포함(가능한 범위)
    """
    d = on or today_krx_str()
    from datetime import datetime, timedelta
    from pykrx import stock

    for _ in range(40):
        try:
            # 어떤 pykrx 버전은 market 파라미터 지원
            df1 = stock.get_market_cap_by_ticker(d, market="KOSPI")
            df2 = stock.get_market_cap_by_ticker(d, market="KOSDAQ")
            df = pd.concat([df1, df2], axis=0)
        except Exception:
            df = stock.get_market_cap_by_ticker(d)

        if df is not None and (not df.empty):
            df = df.copy()
            df.index = df.index.map(lambda x: _ticker6(str(x)))
            df["__asof__"] = d
            return df

        d = ymd(datetime.strptime(d, "%Y%m%d") - timedelta(days=1))

    return pd.DataFrame()


@st.cache_data(show_spinner=False, ttl=60*30)
def krx_year_end_mktcap(ticker6: str, end_year: int, n_years: int) -> pd.DataFrame:
    """
    연도말(각 연도 마지막 영업일) 시총 시계열
    반환: Year, MktCap, MktCap_date
    """
    from datetime import datetime, timedelta
    from pykrx import stock

    t = _ticker6(ticker6)
    years = list(range(int(end_year) - int(n_years) + 1, int(end_year) + 1))
    rows = []

    for y in years:
        d = f"{y}1231"
        mktcap = None
        mktcap_date = None
        for _ in range(40):
            try:
                df = stock.get_market_cap_by_ticker(d)
            except Exception:
                df = None
            if df is not None and (not df.empty) and t in df.index:
                r = df.loc[t]
                mktcap = float(r.get("시가총액", np.nan))
                mktcap_date = d
                break
            d = ymd(datetime.strptime(d, "%Y%m%d") - timedelta(days=1))

        rows.append({"Year": y, "MktCap": mktcap, "MktCap_date": mktcap_date})

    return pd.DataFrame(rows).sort_values("Year", ascending=False).reset_index(drop=True)


def recommend_peers_by_mktcap(base_ticker6: str, k: int = 10, on: str | None = None) -> pd.DataFrame:
    """
    시총 유사 종목 자동 추천(가능하면 섹터까지 동일하게 필터)
    반환: ticker6, 종목명, 시총, diff, asof
    """
    base = _ticker6(base_ticker6)
    uni = krx_market_cap_universe(on)
    if uni is None or uni.empty or base not in uni.index:
        return pd.DataFrame()

    asof = str(uni["__asof__"].iloc[0]) if "__asof__" in uni.columns and len(uni) > 0 else (on or today_krx_str())
    base_cap = pd.to_numeric(uni.loc[base].get("시가총액", np.nan), errors="coerce")
    if pd.isna(base_cap):
        return pd.DataFrame()

    df = uni.copy()
    df = df[df.index != base].copy()
    df["mktcap"] = pd.to_numeric(df.get("시가총액", np.nan), errors="coerce")
    df = df.dropna(subset=["mktcap"])
    if df.empty:
        return pd.DataFrame()

    # (선택) 섹터 동일 필터 시도: pykrx 버전에 따라 함수명이 다를 수 있어 방어적으로 처리
    base_sector = None
    try:
        from pykrx import stock
        sector_func_names = [
            "get_market_sector_classification_by_ticker",
            "get_market_sector_classification",
            "get_market_sector_classifications",
        ]
        sector_df = None
        for fn in sector_func_names:
            if hasattr(stock, fn):
                try:
                    sector_df = getattr(stock, fn)(asof)
                    break
                except Exception:
                    sector_df = None
        if sector_df is not None and (not sector_df.empty) and base in sector_df.index:
            base_sector = str(sector_df.loc[base].iloc[0])
            # sector_df 첫 컬럼을 섹터로 간주
            sec_col = sector_df.columns[0]
            df = df.join(sector_df[[sec_col]].rename(columns={sec_col: "sector"}), how="left")
            df = df[df["sector"].astype(str) == base_sector]
    except Exception:
        pass

    df["diff"] = (df["mktcap"] - float(base_cap)).abs()
    df = df.sort_values("diff", ascending=True).head(int(k)).copy()

    name_col = "종목명" if "종목명" in df.columns else None
    out = pd.DataFrame({
        "ticker6": df.index.astype(str),
        "종목명": df[name_col].astype(str) if name_col else "",
        "시총": df["mktcap"].astype(float),
        "diff": df["diff"].astype(float),
        "asof": asof
    })
    return out.reset_index(drop=True)



@st.cache_data(show_spinner=False, ttl=60*30)
def krx_fundamental_on(ticker6: str, on: str) -> dict:
    # 특정 일자(예: 12/31) 기준 PER/PBR 등을 가져오되, 휴장이면 과거로 롤백
    # (pykrx 내부 버그/휴장 응답 형태로 KeyError가 날 수 있어 try/except로 방어)
    t = _ticker6(ticker6)
    d = on
    for _ in range(40):
        try:
            df = stock.get_market_fundamental_by_ticker(d)
        except Exception:
            df = None

        if df is not None and (not df.empty) and t in df.index:
            r = df.loc[t]

            def _nan_to_none(x):
                try:
                    x = float(x)
                    if np.isnan(x) or np.isinf(x):
                        return None
                    return x
                except Exception:
                    return None

            return {
                "date": d,
                "PER": _nan_to_none(r.get("PER", np.nan)),
                "PBR": _nan_to_none(r.get("PBR", np.nan)),
                "EPS": _nan_to_none(r.get("EPS", np.nan)),
                "BPS": _nan_to_none(r.get("BPS", np.nan)),
                "DIV": _nan_to_none(r.get("DIV", np.nan)),
            }

        d = ymd(datetime.strptime(d, "%Y%m%d") - timedelta(days=1))

    return {"date": None, "PER": None, "PBR": None, "EPS": None, "BPS": None, "DIV": None}



@st.cache_data(show_spinner=False, ttl=60 * 30)
def krx_index_returns(index_ticker: str, start: str, end: str) -> pd.Series:
    """Return daily pct returns for a market index.
    - Primary: pykrx (index code e.g., '1001' for KOSPI, '2001' for KOSDAQ)
    - Fallback: FinanceDataReader (e.g., KS11/KQ11) when KRX is unavailable.
    """
    def _ymd_to_dash(s: str) -> str:
        s = str(s).strip()
        if len(s) == 8 and s.isdigit():
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        return s

    # 1) Try KRX via pykrx (works when KRX is reachable)
    try:
        df = stock.get_index_ohlcv_by_date(start, end, index_ticker)
        if df is not None and not df.empty and "종가" in df.columns:
            ret = df["종가"].pct_change().dropna()
            ret.index = pd.to_datetime(ret.index)
            return ret
    except Exception:
        pass

    # 2) Fallback via FinanceDataReader
    #    pykrx index code -> FDR code mapping
    idx_map = {
        "1001": "KS11",  # KOSPI
        "2001": "KQ11",  # KOSDAQ
    }
    fdr_code = idx_map.get(str(index_ticker).strip(), str(index_ticker).strip())
    try:
        df2 = fdr.DataReader(fdr_code, _ymd_to_dash(start), _ymd_to_dash(end))
        if df2 is None or df2.empty:
            return pd.Series(dtype=float)
        col = "Close" if "Close" in df2.columns else ("종가" if "종가" in df2.columns else df2.columns[0])
        ret2 = df2[col].pct_change().dropna()
        ret2.index = pd.to_datetime(ret2.index)
        return ret2
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(show_spinner=False, ttl=60 * 30)
def krx_stock_returns(stock_code: str, start: str, end: str) -> pd.Series:
    """Return daily pct returns for a stock.
    - Primary: pykrx (KRX data)
    - Fallback: FinanceDataReader (when KRX is unavailable)
    """
    def _ymd_to_dash(s: str) -> str:
        s = str(s).strip()
        if len(s) == 8 and s.isdigit():
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        return s

    # 1) Try KRX via pykrx
    try:
        df = stock.get_market_ohlcv_by_date(start, end, stock_code)
        if df is not None and not df.empty and "종가" in df.columns:
            ret = df["종가"].pct_change().dropna()
            ret.index = pd.to_datetime(ret.index)
            return ret
    except Exception:
        pass

    # 2) Fallback via FinanceDataReader
    try:
        df2 = fdr.DataReader(str(stock_code).strip(), _ymd_to_dash(start), _ymd_to_dash(end))
        if df2 is None or df2.empty:
            return pd.Series(dtype=float)
        col = "Close" if "Close" in df2.columns else ("종가" if "종가" in df2.columns else df2.columns[0])
        ret2 = df2[col].pct_change().dropna()
        ret2.index = pd.to_datetime(ret2.index)
        return ret2
    except Exception:
        return pd.Series(dtype=float)



def compute_beta_ols(stock_ret: pd.Series, market_ret: pd.Series, min_obs: int = 60) -> float | None:
    """
    OLS beta = Cov(rs, rm) / Var(rm)
    - stock_ret / market_ret: 일간 수익률(Series)
    - min_obs: 최소 관측치(기본 60)
    """
    if stock_ret is None or market_ret is None:
        return None

    rs = pd.to_numeric(stock_ret, errors="coerce")
    rm = pd.to_numeric(market_ret, errors="coerce")
    df = pd.concat([rs.rename("rs"), rm.rename("rm")], axis=1).dropna()

    if df.empty or len(df) < min_obs:
        return None

    x = df["rm"].to_numpy(dtype=float)
    y = df["rs"].to_numpy(dtype=float)

    var_x = np.var(x, ddof=1)
    if not np.isfinite(var_x) or var_x == 0:
        return None

    cov_xy = np.cov(y, x, ddof=1)[0, 1]
    beta = cov_xy / var_x
    if not np.isfinite(beta):
        return None

    return float(beta)


# =========================================================
# 7) EV/EBITDA (DART로 EBITDA/현금/차입금 찾기)
# =========================================================
def _norm(s: str) -> str:
    return (s or "").replace(" ", "").replace("\u3000", "").strip()

def _to_num(x):
    try:
        if x is None:
            return None
        if isinstance(x, (int, float, np.floating)):
            if np.isnan(x):
                return None
            return float(x)
        s = str(x).replace(",", "").strip()
        if s == "":
            return None
        return float(s)
    except Exception:
        return None

def _pick_first_amount(df: pd.DataFrame, name_candidates: list[str], amount_col: str = "thstrm_amount") -> float | None:
    if df is None or df.empty:
        return None
    df2 = df.copy()
    df2["account_nm_n"] = df2["account_nm"].astype(str).map(_norm)
    for cand in name_candidates:
        c = _norm(cand)
        hit = df2[df2["account_nm_n"].str.contains(c, na=False)]
        if not hit.empty:
            v = _to_num(hit.iloc[0].get(amount_col))
            if v is not None:
                return v
    return None


def extract_net_debt_and_ebitda(dart_df):
    """
    - 총차입금(core) = 단기차입금 + 유동성장기차입금/유동성장기부채 + 장기차입금 + 사채(전환/신주인수권 포함)
      (리스부채 제외: 사용자가 사업보고서에서 흔히 합산하는 방식에 맞춤)
    - 총차입금(ib)   = 가능한 경우 '이자발생부채/차입금및사채/총차입금' 라인을 우선 사용,
                     없으면 core + 리스부채(추정)까지 포함
    - 현금 = 현금및현금성자산(및 단기금융상품 등 포함 가능)
    - EBITDA = 영업이익 + 감가/상각(감가상각비 + 무형자산상각비 등)
    - CAPEX = (유형+무형 등) 취득 현금유출(처분 유입 제외)

    반환 key:
      net_debt, ebitda, op, da, debt_total(=ib), debt_total_core, cash_total, capex
    """
    import pandas as pd
    import numpy as np

    base_none = {
        "net_debt": None,
        "ebitda": None,
        "op": None,
        "da": None,
        "debt_total": None,        # ib
        "debt_total_core": None,   # core(리스 제외)
        "cash_total": None,
        "capex": None,
    }

    if dart_df is None or getattr(dart_df, "empty", True):
        return base_none

    df = dart_df.copy()

    def _num(x):
        try:
            if x is None:
                return None
            s = str(x).strip()
            if s in ("", "-", "nan", "None"):
                return None
            s = s.replace(",", "")
            if s.startswith("(") and s.endswith(")"):
                s = "-" + s[1:-1]
            return float(s)
        except Exception:
            return None

    def _pick_amt(row):
        # DART: thstrm_amount 또는 thstrm_add_amount에 값이 들어올 수 있음
        for col in ("thstrm_amount", "thstrm_add_amount"):
            if col in row:
                v = _num(row.get(col))
                if v is not None and np.isfinite(v):
                    return float(v)
        return None

    df["_amt"] = df.apply(_pick_amt, axis=1)
    df = df[df["_amt"].notna()]
    if df.empty:
        return base_none

    df["_nm"] = df.get("account_nm", "").astype(str).str.replace(" ", "").str.strip()
    df["_sj"] = df.get("sj_nm", "").astype(str).str.replace(" ", "").str.strip()
    df["_sj_div"] = df.get("sj_div", "").astype(str).str.replace(" ", "").str.strip()

    def _first(_df, cands):
        for c in cands:
            hit = _df[_df["_nm"].str.contains(c, na=False)]
            if not hit.empty:
                return float(hit.iloc[0]["_amt"])
        return None

    def _sum(_df, cands, exclude=None):
        mask = pd.Series(False, index=_df.index)
        for c in cands:
            mask = mask | _df["_nm"].str.contains(c, na=False)
        if exclude:
            for ex in exclude:
                mask = mask & (~_df["_nm"].str.contains(ex, na=False))
        hit = _df[mask]
        if hit.empty:
            return None
        return float(hit["_amt"].sum())

    # -------------------------
    # 1) 영업이익(IS/CIS)
    # -------------------------
    op = _first(df, ["영업이익", "영업손익", "영업이익(손실)", "영업손실"])

    # -------------------------
    # 2) 감가/상각(유무형) - 회사별 포맷 차이로 결측 가능 (우선 최대한 탐색)
    # -------------------------
    EXC_COMMON = ["충당", "손상", "감액", "환입", "평가", "누계", "누적", "상각누계", "감가상각누계"]
    EXC_FIN = ["사채", "할인", "프리미엄", "발행", "차금", "금융", "이자", "수수료", "파생", "환율", "지분법"]
    EXC_ASSET_SALE = ["처분", "매각", "매출", "양도", "손익"]

    stmt = df[
        df["_sj_div"].isin(["IS", "CIS", "CF"])
        | df["_sj"].str.contains("손익", na=False)
        | df["_sj"].str.contains("포괄", na=False)
        | df["_sj"].str.contains("현금흐름", na=False)
    ].copy()
    if stmt.empty:
        stmt = df.copy()

    def _pick_da_best(_df):
        v = _sum(
            _df,
            ["감가상각비및무형자산상각비", "감가상각비및상각비", "감가상각비및무형자산상각비(유무형)"],
            exclude=EXC_COMMON + EXC_FIN + EXC_ASSET_SALE
        )
        if v is not None:
            return float(abs(v))

        dep = _sum(
            _df,
            ["유형자산감가상각비", "사용권자산감가상각비", "감가상각비", "감가상각"],
            exclude=EXC_COMMON + EXC_FIN + EXC_ASSET_SALE
        )
        amo = _sum(
            _df,
            ["무형자산상각비", "무형자산상각", "상각비"],
            exclude=EXC_COMMON + EXC_FIN + EXC_ASSET_SALE
        )
        if dep is not None or amo is not None:
            return float(abs((dep or 0.0) + (amo or 0.0)))
        return None

    is_df = stmt[stmt["_sj_div"].isin(["IS", "CIS"]) | stmt["_sj"].str.contains("손익", na=False) | stmt["_sj"].str.contains("포괄", na=False)]
    da = _pick_da_best(is_df) if not is_df.empty else None
    if da is None:
        cf_df = stmt[stmt["_sj_div"].isin(["CF"]) | stmt["_sj"].str.contains("현금흐름", na=False)]
        da = _pick_da_best(cf_df) if not cf_df.empty else None

    # -------------------------
    # 3) BS 기반 총차입금/현금 산정
    # -------------------------
    bs = df[df["_sj_div"].isin(["BS"]) | df["_sj"].str.contains("재무상태", na=False)].copy()
    if bs.empty:
        bs = df.copy()

    # 3-1) 총차입금(core): 네가 말한 방식에 최대한 맞춤
    debt_core = _sum(
        bs,
        ["단기차입금", "유동성장기차입금", "유동성장기부채", "장기차입금", "사채", "전환사채", "신주인수권부사채"],
        exclude=["상환", "이자", "비용", "수익", "처분", "매각"]
    )

    # 3-2) 총차입금(ib): 가능한 총액 라인이 있으면 그걸 우선
    debt_ib = _first(bs, ["이자발생부채", "차입금및사채", "총차입금"])
    if debt_ib is None:
        lease = _sum(bs, ["리스부채", "유동성리스부채", "비유동리스부채", "사용권부채"], exclude=["이자", "비용", "수익"])
        debt_ib = (debt_core or 0.0) + (lease or 0.0) if (debt_core is not None or lease is not None) else None

    # 3-3) 현금 및 현금성(필요시 단기금융상품 포함)
    cash_total = _first(bs, ["현금및현금성자산및단기금융상품", "현금및현금성자산"])
    if cash_total is None:
        cash_total = _sum(bs, ["현금및현금성자산", "단기금융상품", "현금성자산", "기말현금및현금성자산"], exclude=["제한", "담보"])

    net_debt = None
    if debt_ib is not None and cash_total is not None:
        net_debt = float(debt_ib - cash_total)

    # -------------------------
    # 4) CAPEX(유무형) - CF에서 넓게 매칭 (처분 유입 제외)
    # -------------------------
    capex_raw = _sum(
        df,
        ["유형자산의취득", "유형자산취득", "무형자산의취득", "무형자산취득", "사용권자산의취득", "사용권자산취득",
         "건설중인자산의취득", "건설중인자산취득"],
        exclude=["처분", "매각", "손상", "감액", "환입", "매출", "상각"]
    )
    capex = float(abs(capex_raw)) if capex_raw is not None and np.isfinite(capex_raw) else None

    ebitda = None
    if op is not None and da is not None:
        ebitda = float(op + da)

    return {
        "net_debt": net_debt,
        "ebitda": ebitda,
        "op": op,
        "da": da,
        "debt_total": debt_ib,          # ib
        "debt_total_core": debt_core,   # core
        "cash_total": cash_total,
        "capex": capex,
    }


@st.cache_data(show_spinner=False, ttl=60 * 60)
def ev_ebitda_history(crtfc_key, corp_code, stock_code_6, end_year, n_years=5,
                      reprt_code="11011", fs_div="CFS", shares_override=None):
    """
    연도별 EV/EBITDA 직접계산 히스토리
    - EV = 시총(MktCap) + 순차입금(Net Debt)
    - EBITDA = 영업이익 + 감가/상각
    - 시총은 KRX(시장데이터) 기반. KRX에서 상장주식수 못 가져오면 shares_override(수동입력 주식수)로 보정
    """

    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    from pykrx import stock

    def _ymd(dt):
        return dt.strftime("%Y%m%d")

    def _krx_mktcap_snapshot_asof(ticker6, asof_dt, shares_override=None):
        # asof_dt가 휴장일이면 최대 14일 전까지 롤백
        for i in range(0, 14):
            d = asof_dt - timedelta(days=i)
            ymd = _ymd(d)

            # 1) market cap by ticker (시총/상장주식수)
            try:
                cap_df = stock.get_market_cap_by_ticker(ymd)
            except Exception:
                cap_df = None

            mktcap = None
            shares = None
            if cap_df is not None and not cap_df.empty and ticker6 in cap_df.index:
                row = cap_df.loc[ticker6]
                if "시가총액" in row.index:
                    mktcap = float(row["시가총액"])
                if "상장주식수" in row.index:
                    shares = float(row["상장주식수"])

            # 2) close price
            close = None
            try:
                ohl = stock.get_market_ohlcv_by_date(ymd, ymd, ticker6)
                if ohl is not None and not ohl.empty and "종가" in ohl.columns:
                    close = float(ohl["종가"].iloc[-1])
            except Exception:
                close = None

            # 3) shares override 우선 반영
            if shares_override is not None and float(shares_override) > 0:
                shares = float(shares_override)

            # 4) mktcap 없으면 close*shares로 계산
            if (mktcap is None or not np.isfinite(mktcap)) and close is not None and shares is not None:
                mktcap = float(close * shares)

            if mktcap is not None and np.isfinite(mktcap):
                return {"date": d, "mktcap": mktcap, "shares": shares, "close": close}

        return None

    years = list(range(end_year - n_years + 1, end_year + 1))
    rows = []

    for y in years:
        # 1) DART에서 BS/IS/CF 전체 계정 조회
        dart_df = dart_all_accounts(crtfc_key, corp_code, str(y), reprt_code=reprt_code, fs_div=fs_div)

        # 2) NetDebt / EBITDA 추출
        nd_e = extract_net_debt_and_ebitda(dart_df)
        net_debt = nd_e.get("net_debt")
        ebitda = nd_e.get("ebitda")

        # 3) 연말 시총 (휴장일 보정 포함)
        asof_dt = datetime(y, 12, 31)
        snap = _krx_mktcap_snapshot_asof(stock_code_6, asof_dt, shares_override=shares_override)

        mktcap = snap["mktcap"] if snap else None
        mktcap_date = snap["date"].strftime("%Y-%m-%d") if snap else None

        # 4) EV/EBITDA 계산
        ev = None
        multiple = None
        if mktcap is not None and net_debt is not None:
            ev = float(mktcap + net_debt)
        if ev is not None and ebitda is not None and ebitda != 0:
            multiple = float(ev / ebitda)

        rows.append({
            "Year": y,
            "MktCap": mktcap,
            "NetDebt": net_debt,
            "EBITDA": ebitda,
            "EV": ev,
            "EV/EBITDA": multiple,
            "MktCap_date": mktcap_date
        })

    df_out = pd.DataFrame(rows).sort_values("Year", ascending=False).reset_index(drop=True)
    return df_out


@st.cache_data(show_spinner=False, ttl=60 * 60)
def debt_cash_da_capex_history(crtfc_key, corp_code, end_year, n_years=5,
                               reprt_code="11011", fs_div="CFS", debt_mode: str = "core"):
    """
    연도별 표(시장 탭 하단용)
    - debt_mode:
        "core" : 단기차입금+유동성장기부채/차입금+장기차입금+사채(리스 제외)
        "ib"   : 이자발생부채/차입금및사채 등 가능하면 총액 우선(리스 포함 가능)
    """
    import pandas as pd
    import numpy as np

    years = list(range(int(end_year) - int(n_years) + 1, int(end_year) + 1))
    rows = []
    for y in years:
        dart_df = dart_all_accounts(crtfc_key, corp_code, str(y), reprt_code=reprt_code, fs_div=fs_div)
        d = extract_net_debt_and_ebitda(dart_df)

        debt_val = d.get("debt_total_core") if str(debt_mode) == "core" else d.get("debt_total")

        rows.append({
            "Year": y,
            "총차입금": debt_val,
            "현금 및 현금성 자산": d.get("cash_total"),
            "영업이익": d.get("op"),
            "감가상각비(유무형)": d.get("da"),
            "CAPEX": d.get("capex"),
        })

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out = out.sort_values("Year", ascending=False).reset_index(drop=True)

    for c in ["총차입금", "현금 및 현금성 자산", "영업이익", "감가상각비(유무형)", "CAPEX"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    out.replace([np.inf, -np.inf], np.nan, inplace=True)
    return out




# =========================================================
# 8) Ratios + Commentary
# =========================================================
def compute_fin_ratios(wide: pd.DataFrame):
    _, rev_s = pick_by_alias(wide, "REV")
    _, op_s  = pick_by_alias(wide, "OP")
    _, ni_s  = pick_by_alias(wide, "NI")
    _, asset_s = pick_by_alias(wide, "ASSET")
    _, eq_s = pick_by_alias(wide, "EQUITY")
    _, liab_s = pick_by_alias(wide, "LIAB")
    _, ca_s = pick_by_alias(wide, "CA")
    _, cl_s = pick_by_alias(wide, "CL")

    rev = pd.to_numeric(rev_s, errors="coerce") if rev_s is not None else None
    op  = pd.to_numeric(op_s, errors="coerce") if op_s is not None else None
    ni  = pd.to_numeric(ni_s, errors="coerce") if ni_s is not None else None
    asset = pd.to_numeric(asset_s, errors="coerce") if asset_s is not None else None
    eq    = pd.to_numeric(eq_s, errors="coerce") if eq_s is not None else None
    liab  = pd.to_numeric(liab_s, errors="coerce") if liab_s is not None else None
    ca    = pd.to_numeric(ca_s, errors="coerce") if ca_s is not None else None
    cl    = pd.to_numeric(cl_s, errors="coerce") if cl_s is not None else None

    out = {}
    out["OPM"] = (op / rev) if (rev is not None and op is not None) else None
    out["NPM"] = (ni / rev) if (rev is not None and ni is not None) else None
    out["ROE"] = (ni / eq) if (ni is not None and eq is not None) else None
    out["ROA"] = (ni / asset) if (ni is not None and asset is not None) else None
    out["Debt_to_Equity"] = (liab / eq) if (liab is not None and eq is not None) else None
    out["Current_Ratio"] = (ca / cl) if (ca is not None and cl is not None) else None
    out["NWC"] = (ca - cl) if (ca is not None and cl is not None) else None
    out["Asset_Turnover"] = (rev / asset) if (rev is not None and asset is not None) else None

    # 비유동비율(일반적으로): 비유동자산 / 자기자본
    if (asset is not None) and (ca is not None) and (eq is not None):
        nca = (asset - ca)
        out["NonCurrent_Asset_Ratio"] = (nca / eq)
    else:
        out["NonCurrent_Asset_Ratio"] = None

    base = {"rev": rev, "op": op, "ni": ni, "asset": asset, "eq": eq, "liab": liab, "ca": ca, "cl": cl}
    return out, base







def _fmt_pct(x: float | None, digits=1) -> str:
    if x is None or (isinstance(x, float) and (np.isnan(x) or not np.isfinite(x))):
        return "-"
    return f"{x*100:.{digits}f}%"

def _fmt_pp(x: float | None, digits=1) -> str:
    sign = "+" if x is not None and x >= 0 else ""
    return "-" if x is None else f"{sign}{x*100:.{digits}f}%p"

def _fmt_money(x: float | None, unit: str) -> str:
    if x is None or (isinstance(x, float) and (np.isnan(x) or not np.isfinite(x))):
        return "-"
    if is_trillion_mode(unit):
        return f"{x/1_000_000_000_000:,.3f}조"
    return f"{x:,.0f}"

def _safe_cagr(series: pd.Series, years_back: int = 3) -> float | None:
    if series is None:
        return None
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < years_back:
        return None
    ss = s.sort_index()
    y0, yN = float(ss.iloc[-years_back]), float(ss.iloc[-1])
    if y0 <= 0 or yN <= 0:
        return None
    return (yN / y0) ** (1 / (years_back - 1)) - 1

def _yoy_display(curr, prev, unit):
    if curr is None or prev is None:
        return "-", "데이터 부족"
    delta = curr - prev
    if prev <= 0 or abs(prev) < abs(curr) * 0.05:
        if prev < 0 and curr >= 0:
            return "흑자전환", f"Δ {_fmt_money(delta, unit)}"
        if prev >= 0 and curr < 0:
            return "적자전환", f"Δ {_fmt_money(delta, unit)}"
        return "변동 큼", f"Δ {_fmt_money(delta, unit)}"
    return f"{(curr/prev - 1)*100:.1f}%", f"Δ {_fmt_money(delta, unit)}"




def render_commentary_box(title: str, bullets: list[str], badges: list[tuple[str, str]] | None = None):
    badge_htmls = ""
    if badges:
        badge_htmls = "".join([badge_html(t, k) for (t, k) in badges])
    st.markdown(
        f"""
        <div class="comment-box">
          <div class="comment-title">{title}</div>
          <div style="margin-bottom:10px;">{badge_htmls}</div>
          <ul style="margin:0; padding-left:18px; line-height:1.85; color:rgba(15,23,42,0.82);">
            {''.join([f"<li>{b}</li>" for b in bullets])}
          </ul>
        </div>
        """,
        unsafe_allow_html=True
    )




def build_is_commentary(wide: pd.DataFrame, industry_tag: str):
    ratios, base = compute_fin_ratios(wide)
    unit = st.session_state.unit if "unit" in st.session_state else "원"

    rev = pd.to_numeric(base.get("rev"), errors="coerce")
    op  = pd.to_numeric(base.get("op"),  errors="coerce")
    ni  = pd.to_numeric(base.get("ni"),  errors="coerce")

    rev_last, rev_prev = last_value(rev), prev_value(rev)
    op_last,  op_prev  = last_value(op),  prev_value(op)
    ni_last,  ni_prev  = last_value(ni),  prev_value(ni)

    bullets, badges = [], []

    # ── 매출
    rev_yoy, rev_d = _yoy_display(rev_last, rev_prev, unit)
    bullets.append(
        f"매출 : {_fmt_money(rev_last, unit)} / YoY : {rev_yoy} ({rev_d})"
    )

    # ── 영업이익 & 마진
    op_yoy, op_d = _yoy_display(op_last, op_prev, unit)
    bullets.append(
        f"영업이익 : {_fmt_money(op_last, unit)} / YoY : {op_yoy} ({op_d})"
    )

    if rev_last not in (None, 0) and op_last is not None:
        opm_last = op_last / rev_last
        if rev_prev not in (None, 0) and op_prev is not None:
            opm_prev = op_prev / rev_prev
            opm_pp = opm_last - opm_prev
        else:
            opm_pp = None

        bullets.append(
            f"영업이익률(OPM) : {opm_last*100:.1f}%"
            + (f" (전년 대비 {opm_pp*100:+.1f}%p)" if opm_pp is not None else "")
        )

        if opm_pp is not None:
            if opm_pp > 0:
                badges.append(("마진 개선", "ok"))
                bullets.append("마진 개선은 가격 인상·원가 부담 완화·고마진 제품 비중 확대·환율 효과 등 여러 요소가 실적에 긍정적으로 작용.")
            else:
                badges.append(("마진 악화", "warn"))
                bullets.append("마진 악화는 원가 상승·가격 경쟁·고정비 부담·일회성 비용 등 여러 요소가 실적에 부정적으로 작용.")

    # ── 순이익 / 영업외
    ni_yoy, ni_d = _yoy_display(ni_last, ni_prev, unit)
    bullets.append(
        f"순이익 :  {_fmt_money(ni_last, unit)} / YoY : {ni_yoy} ({ni_d})"
    )

    if op_last is not None and ni_last is not None:
        gap = ni_last - op_last
        if abs(gap) > abs(op_last) * 0.5:
            badges.append(("영업외 영향 큼", "warn"))
            bullets.append(
                "순이익과 영업이익의 괴리가 큼. "
                "금융손익·환율·관계기업·일회성 요인 등이 실적을 좌우했을 가능성이 큼."
            )
        else:
            badges.append(("본업 중심", "ok"))
            bullets.append("순이익이 영업이익의 괴리가 크지 않아 회사 실적이 본업 성과로 설명된다.")

    # ── 애널리스트 체크포인트
    bullets.append(
        "체크포인트 : 실적 변화의 원인은 ① 매출(물량 vs 단가)"
        " ② 마진 변화(원가/고정비/믹스/환율/일회성) 등으로 나눠 해석하는 것이 핵심"
    )

    return bullets, badges




def build_bs_commentary(wide: pd.DataFrame, industry_tag: str):
    ratios, base = compute_fin_ratios(wide)
    unit = st.session_state.unit if "unit" in st.session_state else "원"

    eq   = pd.to_numeric(base.get("eq"), errors="coerce")
    liab = pd.to_numeric(base.get("liab"), errors="coerce")
    ca   = pd.to_numeric(base.get("ca"), errors="coerce")
    cl   = pd.to_numeric(base.get("cl"), errors="coerce")

    eq_last, liab_last = last_value(eq), last_value(liab)
    ca_last, cl_last = last_value(ca), last_value(cl)

    bullets, badges = [], []

    bullets.append(
        f"자본 : {_fmt_money(eq_last, unit)} / "
        f"부채 : {_fmt_money(liab_last, unit)}"
    )

    if eq_last not in (None, 0) and liab_last is not None:
        dte = liab_last / eq_last
        bullets.append(f"부채/자본(D/E) : {dte*100:.0f}%")
        if dte >= 200:
            badges.append(("레버리지 높음", "warn"))
            bullets.append("레버리지가 높아 금리·차환 리스크에 민감.")
        else:
            badges.append(("레버리지 관리 가능", "ok"))

    if ca_last is not None and cl_last not in (None, 0):
        cr = ca_last / cl_last
        cr_pct = cr * 100
        bullets.append(f"유동비율 : {cr_pct:.0f}%")
        
        if cr < 1.0:
            badges.append(("유동성 주의", "warn"))
            bullets.append("유동비율이 100% 미만으로 단기 상환 여력에 부담 가능. 현금흐름/차환 계획 점검 필요.")
        elif cr < 1.5:
            badges.append(("유동성 보통", "info"))
            bullets.append("유동비율이 100~150% 구간. 단기 유동성은 무난하나 유동자산 구성(현금·매출채권·재고) 점검 권장.")
        elif cr < 2.0:
            badges.append(("유동성 양호", "ok"))
            bullets.append("유동비율이 150~200%로 단기 유동성은 양호한 편. 유동자산 구성과 단기차입 만기구조를 함께 확인하면 충분.")
        else:
            badges.append(("유동성 매우 양호", "ok"))
            bullets.append("유동비율이 200% 이상으로 단기 유동성은 매우 안정적. 다만 과잉 운전자본(재고/채권 누적) 여부는 체크.")
    else:
        bullets.append("유동비율 : - (유동자산/유동부채 데이터 부족)")

    bullets.append(
        "체크포인트: 차입금 만기 구조 / 유동부채 구성 / 재고·매출채권 회전"
    )

    return bullets, badges




# =========================================================
# 9) DCF / WACC
# =========================================================
def build_fcff_forecast(base_year, base_revenue, horizon, sales_cagr, op_margin,
                        tax_rate, da_pct_sales, capex_pct_sales, nwc_pct_sales):
    years = [base_year + i for i in range(1, horizon + 1)]
    rev, ebit, nopat, da, capex, nwc, delta_nwc, fcff = [], [], [], [], [], [], [], []
    prev_rev = base_revenue
    prev_nwc = base_revenue * nwc_pct_sales

    for _ in years:
        r = prev_rev * (1 + sales_cagr)
        rev.append(r)

        e = r * op_margin
        ebit.append(e)

        n = e * (1 - tax_rate)
        nopat.append(n)

        d = r * da_pct_sales
        da.append(d)

        c = r * capex_pct_sales
        capex.append(c)

        n_wc = r * nwc_pct_sales
        nwc.append(n_wc)

        d_nwc = n_wc - prev_nwc
        delta_nwc.append(d_nwc)

        f = n + d - c - d_nwc
        fcff.append(f)

        prev_rev = r
        prev_nwc = n_wc

    return pd.DataFrame({
        "Year": years,
        "Revenue": rev, "EBIT": ebit, "NOPAT": nopat,
        "D&A": da, "CAPEX": capex, "NWC": nwc, "ΔNWC": delta_nwc, "FCFF": fcff
    })

def dcf_valuation(fcff_df, wacc, terminal_g, net_debt, shares_outstanding):
    fcff = fcff_df["FCFF"].values.astype(float)
    years = np.arange(1, len(fcff) + 1, dtype=float)

    disc = 1 / ((1 + wacc) ** years)
    pv_fcff = float(np.sum(fcff * disc))

    last_fcff = float(fcff[-1])
    tv = last_fcff * (1 + terminal_g) / (wacc - terminal_g)
    pv_tv = float(tv * disc[-1])

    ev = pv_fcff + pv_tv
    equity = ev - net_debt
    price = equity / shares_outstanding if shares_outstanding > 0 else np.nan
    tv_share = (pv_tv / ev) if ev != 0 else np.nan

    return {"PV_FCFF": pv_fcff, "PV_TV": pv_tv, "EV": ev, "Equity": equity, "Price": price, "TV_Share": tv_share}

def calc_wacc_from_inputs(rf, beta, mrp, kd, tax_rate, debt_weight):
    ke = rf + beta * mrp
    dw = float(np.clip(debt_weight, 0.0, 1.0))
    ew = 1.0 - dw
    wacc = ew * ke + dw * kd * (1 - tax_rate)
    return ke, wacc

# =========================================================
# 10) Session State
# =========================================================
REPRT_NAME = {"11011": "사업보고서(연간)", "11012": "반기(누적)", "11013": "1Q(누적)", "11014": "3Q(누적)"}

def init_state():
    defaults = {
        "page": "0 홈",
        "unit": "원",

        "corp_candidates": pd.DataFrame(),
        "selected_corp_code": "",
        "company_info": None,
        "wide": None,
        "wide_is": None,

        "year_to_term": {},
        "report_ready": False,

        "industry_tag": "자동/미지정",
        "reprt_code": "11011",
        "fs_div": "CFS",
        "picked_row_idx": None,

        "market_ok": False,
        "market_msg": "",
        "mktcap": None,
        "shares": None,
        "close": None,
        "mkt_date": None,
        "fund": None,
        "price_df": pd.DataFrame(),

        "beta_ok": False,
        "beta_val": None,
        "beta_msg": "",

        "evhist": pd.DataFrame(),

        "peer_input": "",
        "peer_rows": pd.DataFrame(),
        "peer_ok": False,
        "peer_msg": "",
        "peer_stats": {},

        "last_dcf": None,
        "wc_bs": pd.DataFrame(),

        # ✅ (추가) 한국은행 ECOS 채권지표용
        "bok_ecos_key": "",
        "bond_latest": pd.DataFrame(),
        "bond_msg": "",
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_all():
    st.session_state.clear()
    init_state()

init_state()

# =========================================================
# 11) UI Components
# =========================================================
def render_header():
    st.markdown(
        """
        <div class="header-wrap">
          <div class="header-card">
            <div class="header-title">📊Valuation</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def kpi(col, label, value, sub=""):
    # sub가 비어있으면 동일한 카드 높이를 위해 한 줄 공간을 유지
    safe_sub = sub if (sub is not None and str(sub).strip() != "") else "&nbsp;"
    col.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-sub">{safe_sub}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_top_nav(reprt_code: str, fs_div: str):
    left, right = st.columns([1.2, 3.8], vertical_alignment="center")
    with left:
        unit = st.radio(
            "단위",
            ["원", "조원"],
            horizontal=True,
            label_visibility="collapsed",
            index=0 if st.session_state.unit == "원" else 1,
            key="top_unit",
        )
        st.session_state.unit = unit

    with right:
        pages = ["0 홈", "1 손익(IS)", "2 재무상태(BS)", "3 시장/멀티플", "4 Peer", "5 DCF/WACC", "6 채권지표"]
        cur = st.session_state.page if st.session_state.page in pages else "0 홈"
        page = st.radio(
            "페이지",
            pages,
            horizontal=True,
            label_visibility="collapsed",
            index=pages.index(cur),
            key="top_page",
        )
        st.session_state.page = page

        badges = []
        badges.append((f"{REPRT_NAME.get(reprt_code, reprt_code)}", "info" if reprt_code == "11011" else "warn"))
        badges.append((f"{'연결(CFS)' if fs_div=='CFS' else '별도(OFS)'}", "info"))

        if st.session_state.industry_tag and str(st.session_state.industry_tag).strip() != "":
            itag = str(st.session_state.industry_tag).strip()
            badges.append((f"업종: {itag}", "note"))

        badges.append(("시장데이터: KRX OK", "ok") if st.session_state.market_ok else ("시장데이터: KRX X", "warn"))

        if st.session_state.beta_ok and (st.session_state.beta_val is not None) and np.isfinite(st.session_state.beta_val):
            badges.append((f"β: {float(st.session_state.beta_val):.2f}", "ok"))
        else:
            badges.append(("β: 미계산", "warn"))

        if st.session_state.peer_ok and (st.session_state.peer_rows is not None) and (not st.session_state.peer_rows.empty):
            badges.append(("Peer: 준비됨", "ok"))
        else:
            badges.append(("Peer: 미설정", "warn"))

        st.markdown(
            "<div style='margin-top:2px;'>"
            + "".join([badge_html(t, k) for t, k in badges])
            + "</div>",
            unsafe_allow_html=True
        )
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)


def render_selected_company(info: dict):
    st.markdown('<div class="section-title">✅ 선택된 회사</div>', unsafe_allow_html=True)
    industry = st.session_state.industry_tag if st.session_state.industry_tag != "자동/미지정" else "미지정(선택 가능)"

    # 좌측에서 선택한 값(기준연도/기간/보고서)을 상단 카드에 표시
    _end_year = st.session_state.get("sb_end_year", None)
    _n_years = st.session_state.get("sb_n_years", None)
    _reprt = st.session_state.get("sb_reprt_label", None)
    _fs = st.session_state.get("sb_fs_div_label", None)

    report_text = []
    if _end_year is not None:
        report_text.append(f"기준연도 {_end_year}")
    if _n_years is not None:
        report_text.append(f"기간 {_n_years}년")
    if _reprt is not None:
        report_text.append(f"보고서 {_reprt}")
    if _fs is not None:
        report_text.append(f"{_fs}")
    report_text = " · ".join(report_text) if report_text else "-"

    c1, c2, c3, c4 = st.columns([2.0, 1.2, 1.6, 1.2])
    with c1:
        # corp_code 제거, 종목코드를 기존 자리(종목코드 라벨)에서 빼고 여기로 붙임(라벨 없이)
        sc = info.get("stock_code", "-") or "-"
        st.markdown(
            f"<div class='card'><b style='font-size:16px;color:#0f172a'>{info.get('corp_name','')}</b><br/>"
            f"<span style='color:rgba(15,23,42,0.72);'>종목:</span> <b style='color:#0f172a'>{sc}</b></div>",
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(f"<div class='card'>시장구분<br/><b style='color:#0f172a'>{corp_cls_to_kor(info.get('corp_cls',''))}</b></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='card'>보고서 설정<br/><b style='color:#0f172a'>{report_text}</b></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='card'>업종(태그)<br/><b style='color:#0f172a'>{industry}</b></div>", unsafe_allow_html=True)

# =========================================================
# 12) Market orchestrator + Beta
# =========================================================

def fetch_market_bundle_krx(stock_code_6: str) -> tuple[bool, str]:
    """
    KRX 시장데이터 번들(정상화):
    - price_df(최근 1년) 확보가 최우선
    - mktcap/shares/fund는 price 마지막 거래일 기준으로 롤백 조회
    - mktcap 미조회 시 close*shares로 내부 계산 fallback
    """
    sc = _ticker6(stock_code_6)
    if not sc or sc == "000000":
        st.session_state.market_ok = False
        st.session_state.market_msg = "종목코드가 없습니다."
        st.session_state.price_df = pd.DataFrame()
        st.session_state.close = None
        st.session_state.mkt_date = None
        st.session_state.mktcap = None
        st.session_state.shares = None
        st.session_state.fund = {}
        return False, st.session_state.market_msg

    def _roll_back_dates(asof_ymd: str, max_back: int = 60) -> list[str]:
        out = []
        d = asof_ymd
        for _ in range(max_back):
            out.append(d)
            try:
                d = ymd(datetime.strptime(d, "%Y%m%d") - timedelta(days=1))
            except Exception:
                break
        return out

    def _fetch_cap_with_rollback(asof_ymd: str) -> dict:
        for d in _roll_back_dates(asof_ymd, max_back=80):
            try:
                dfm = stock.get_market_cap_by_ticker(d)
            except Exception:
                dfm = None
            if dfm is None or dfm.empty or sc not in dfm.index:
                continue

            r = dfm.loc[sc]
            mktcap = _to_num(r.get("시가총액"))
            shares = _to_num(r.get("상장주식수"))
            close_ = _to_num(r.get("종가"))

            return {
                "date": d,
                "mktcap": mktcap,
                "shares": shares,
                "close": close_,
            }
        return {}

    def _fetch_fund_with_rollback(asof_ymd: str) -> dict:
        for d in _roll_back_dates(asof_ymd, max_back=80):
            try:
                dff = stock.get_market_fundamental_by_ticker(d)
            except Exception:
                dff = None
            if dff is None or dff.empty or sc not in dff.index:
                continue

            r = dff.loc[sc]
            return {
                "date": d,
                "PER": _to_num(r.get("PER")),
                "PBR": _to_num(r.get("PBR")),
                "EPS": _to_num(r.get("EPS")),
                "BPS": _to_num(r.get("BPS")),
                "DIV": _to_num(r.get("DIV")),
            }
        return {}

    try:
        # 1) 주가 히스토리(가장 중요)
        end = today_krx_str()
        start = ymd(_now_kst() - timedelta(days=370))
        p = krx_price_history(sc, start, end)  # 내부에서 휴장일 롤백

        close_fix = None
        asof_fix = None
        if p is not None and (not p.empty):
            closes = pd.to_numeric(p.get("Close"), errors="coerce").dropna()
            if not closes.empty:
                close_fix = float(closes.iloc[-1])
                try:
                    asof_fix = pd.to_datetime(p["Date"].iloc[-1]).strftime("%Y%m%d")
                except Exception:
                    asof_fix = today_krx_str()

        ok = (p is not None) and (not p.empty) and (close_fix is not None)

        st.session_state.price_df = p if (p is not None) else pd.DataFrame()
        st.session_state.close = close_fix
        st.session_state.mkt_date = asof_fix
        st.session_state.market_ok = bool(ok)

        if not ok:
            msg = (
                "KRX 주가 데이터를 가져오지 못했습니다. "
                "원인: 휴장일/네트워크/pykrx 응답 지연/차단 가능. "
                "잠시 후 ② 재무 가져오기를 다시 시도해보세요."
            )
            st.session_state.market_msg = msg
            st.session_state.mktcap = None
            st.session_state.shares = None
            st.session_state.fund = {}
            return False, msg

        # 2) 시총/주식수 (price 마지막 거래일 기준으로 롤백)
        cap = _fetch_cap_with_rollback(asof_fix or today_krx_str())
        st.session_state.mktcap = cap.get("mktcap")
        st.session_state.shares = cap.get("shares")

        # close는 price_df가 기준이지만, 혹시 결측이면 cap 종가로 보정
        if (st.session_state.close is None) and (cap.get("close") is not None):
            st.session_state.close = float(cap.get("close"))
        if (st.session_state.mkt_date is None) and cap.get("date"):
            st.session_state.mkt_date = cap.get("date")

        # 3) 펀더멘털 (동일 기준일 롤백)
        fund = _fetch_fund_with_rollback(asof_fix or today_krx_str())
        st.session_state.fund = fund if fund else {}

        # 4) 내부 계산 fallback: mktcap 없으면 close*shares
        if (st.session_state.mktcap is None) and (st.session_state.close is not None) and (st.session_state.shares is not None):
            try:
                st.session_state.mktcap = float(st.session_state.close) * float(st.session_state.shares)
            except Exception:
                pass

        warn = ""
        if st.session_state.mktcap is None or st.session_state.shares is None:
            warn = "주가 데이터는 정상인데 시총/주식수 일부가 비었습니다(휴장/응답결측 가능)."
        if not st.session_state.fund:
            warn = (warn + " " if warn else "") + "PER/PBR/EPS/BPS 일부가 비었습니다(응답결측 가능)."

        st.session_state.market_msg = warn
        return True, warn

    except Exception as e:
        st.session_state.market_ok = False
        st.session_state.market_msg = f"KRX 시장데이터 실패: {e}"
        st.session_state.price_df = pd.DataFrame()
        st.session_state.close = None
        st.session_state.mkt_date = None
        st.session_state.mktcap = None
        st.session_state.shares = None
        st.session_state.fund = {}
        return False, st.session_state.market_msg



def fetch_beta_bundle(stock_code_6: str, market_kind: str, lookback_years: int = 3):
    """
    return: (ok: bool, msg: str, beta: float|None)
    - 1차: pykrx(주식/지수)로 수익률 계산
    - 실패: FinanceDataReader로 fallback
    """
    end0 = today_krx_str()
    start0 = ymd(_now_kst() - timedelta(days=int(365.25 * lookback_years)))

    # pykrx 지수 티커
    idx_ticker = "1001" if market_kind == "KOSPI" else "2001"

    # 1) pykrx: end0가 휴장일이면 최대 10일 뒤로 밀어가며 시도
    used_end = None
    sret = None
    mret = None

    for back in range(0, 11):
        d_try = ymd(_now_kst() - timedelta(days=back))
        try:
            tmp_s = krx_stock_returns(stock_code_6, start0, d_try)
            tmp_m = krx_index_returns(idx_ticker, start0, d_try)
            if tmp_s is not None and tmp_m is not None and (not tmp_s.empty) and (not tmp_m.empty):
                used_end = d_try
                sret = tmp_s
                mret = tmp_m
                break
        except Exception:
            continue

    if used_end is not None:
        beta = compute_beta_ols(sret, mret, min_obs=60)
        if beta is None:
            return (False, "β 계산 실패(관측치 부족/분산 0).", None)
        return (True, f"β 계산 성공(KRX: {start0}~{used_end})", beta)

    # 2) fallback: FinanceDataReader
    try:
        # start0/end0은 'YYYYMMDD' 문자열이므로 datetime으로 변환 후 yyyy-mm-dd로 변환
        start_s = datetime.strptime(start0, "%Y%m%d").strftime("%Y-%m-%d")
        end_s = datetime.strptime(end0, "%Y%m%d").strftime("%Y-%m-%d")

        idx_sym = "KS11" if market_kind == "KOSPI" else "KQ11"
        sym_candidates = [f"{stock_code_6}.KS", f"{stock_code_6}.KQ", stock_code_6]

        def _fdr_returns(sym: str, st_s: str, en_s: str) -> pd.Series | None:
            try:
                df = fdr.DataReader(sym, st_s, en_s)
                if df is None or df.empty:
                    return None
                close_col = "Close" if "Close" in df.columns else ("종가" if "종가" in df.columns else None)
                if close_col is None:
                    return None
                px = pd.to_numeric(df[close_col], errors="coerce").dropna()
                if px.empty:
                    return None
                return px.pct_change().dropna()
            except Exception:
                return None

        sret2 = None
        for sym in sym_candidates:
            sret2 = _fdr_returns(sym, start_s, end_s)
            if sret2 is not None and not sret2.empty:
                break

        mret2 = _fdr_returns(idx_sym, start_s, end_s)

        if sret2 is None or mret2 is None or sret2.empty or mret2.empty:
            return (False, "β 계산 실패(주식/지수 데이터 없음).", None)

        beta2 = compute_beta_ols(sret2, mret2, min_obs=60)
        if beta2 is None:
            return (False, "β 계산 실패(관측치 부족/분산 0).", None)

        return (True, f"β 계산 성공(FDR: {start_s}~{end_s})", beta2)

    except Exception:
        return (False, "β 계산 실패(예외 발생).", None)





# =========================================================
# 13) Peer (KRX 멀티플 + EV/EBITDA 직접 계산)
# =========================================================
def parse_peer_codes(peer_str: str) -> list[str]:
    raw = (peer_str or "").replace("\n", " ").replace("\t", " ").replace(",", " ")
    toks = [t.strip() for t in raw.split(" ") if t.strip()]
    codes = []
    for t in toks:
        digits = "".join([c for c in t if c.isdigit()])
        if digits:
            codes.append(digits.zfill(6))
    return list(dict.fromkeys(codes))

@st.cache_data(show_spinner=False, ttl=60*30)
def krx_peer_fundamentals(codes: list[str]) -> pd.DataFrame:
    d = today_krx_str()
    for _ in range(40):
        dfm = stock.get_market_cap_by_ticker(d)
        dff = stock.get_market_fundamental_by_ticker(d)
        if dfm is not None and not dfm.empty and dff is not None and not dff.empty:
            rows = []
            for c in codes:
                c6 = _ticker6(c)
                row = {"code": c6}
                if c6 in dfm.index:
                    r = dfm.loc[c6]
                    row["close"] = _to_num(r.get("종가"))
                    row["mktcap"] = _to_num(r.get("시가총액"))
                    row["shares"] = _to_num(r.get("상장주식수"))
                if c6 in dff.index:
                    r = dff.loc[c6]
                    row["PER"] = _to_num(r.get("PER"))
                    row["PBR"] = _to_num(r.get("PBR"))
                    row["EPS"] = _to_num(r.get("EPS"))
                    row["BPS"] = _to_num(r.get("BPS"))
                    row["DIV"] = _to_num(r.get("DIV"))
                rows.append(row)
            out = pd.DataFrame(rows)
            out["asof"] = d
            return out
        d = ymd(datetime.strptime(d, "%Y%m%d") - timedelta(days=1))
    return pd.DataFrame()

def peer_stats_from_df(df: pd.DataFrame):
    def _stat(col):
        if col not in df.columns:
            return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None}
        s = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if s.empty:
            return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None}
        return {
            "n": int(len(s)),
            "mean": float(s.mean()),
            "median": float(s.median()),
            "p25": float(np.percentile(s, 25)),
            "p75": float(np.percentile(s, 75)),
        }
    return {"PER": _stat("PER"), "PBR": _stat("PBR"), "EV/EBITDA": _stat("EV/EBITDA")}

def implied_prices_from_peer(peer_stats: dict, our_eps: float | None, our_bps: float | None,
                             our_ebitda: float | None, our_net_debt: float | None, our_shares: float | None):
    per_m = _to_num(peer_stats.get("PER", {}).get("median"))
    pbr_m = _to_num(peer_stats.get("PBR", {}).get("median"))
    evm_m = _to_num(peer_stats.get("EV/EBITDA", {}).get("median"))

    out = {}
    out["PER_price"] = (per_m * our_eps) if (per_m is not None and our_eps is not None) else None
    out["PBR_price"] = (pbr_m * our_bps) if (pbr_m is not None and our_bps is not None) else None

    if evm_m is not None and our_ebitda not in (None, 0) and our_shares not in (None, 0) and our_net_debt is not None:
        target_ev = evm_m * float(our_ebitda)
        target_equity = target_ev - float(our_net_debt)
        out["EVEBITDA_price"] = target_equity / float(our_shares)
        out["EVEBITDA_note"] = ""
    else:
        out["EVEBITDA_price"] = None
        out["EVEBITDA_note"] = "EV/EBITDA 방식은 (우리 EBITDA, NetDebt, 주식수)와 Peer EV/EBITDA가 필요합니다."
    return out

# =========================================================
# 14) Pages
# =========================================================

def render_bond_page():
    import altair as alt

    st.markdown('<div class="section-title">💹 6 채권지표 (한국은행 ECOS)</div>', unsafe_allow_html=True)
    st.caption("상단: 최신 수익률(항상 최신) · 하단: 조회기간(3/5/10년) 선택 시 연도별 데이터/연도평균 표시")

    # =========================
    # 0) API KEY 입력
    # =========================
    st.session_state.bok_ecos_key = st.text_input(
        "한국은행 ECOS API Key",
        type="password",
        placeholder="발급받은 인증키 붙여넣기",
        value=st.session_state.get("bok_ecos_key", ""),
        key="bond_ecos_key_input"
    ).strip()

    ecos_key = st.session_state.bok_ecos_key
    if not ecos_key:
        st.info("ECOS API Key를 입력하면 데이터를 불러옵니다.")
        return

    BASE = "https://ecos.bok.or.kr/api"

    def _ecos_get_json(url: str) -> dict:
        try:
            r = requests.get(url, timeout=12)
            return r.json()
        except Exception as ex:
            return {"RESULT": {"CODE": "ERROR", "MESSAGE": str(ex)}}

    def _result_code_msg(j: dict) -> tuple[str, str]:
        if not isinstance(j, dict):
            return ("", "")
        r = j.get("RESULT")
        if isinstance(r, dict):
            return (str(r.get("CODE", "")), str(r.get("MESSAGE", "")))
        return ("", "")

    @st.cache_data(show_spinner=False, ttl=60 * 60)
    def _ecos_table_list() -> pd.DataFrame:
        url = f"{BASE}/StatisticTableList/{ecos_key}/json/kr/1/2000/"
        j = _ecos_get_json(url)
        root = j.get("StatisticTableList", {})
        rows = root.get("row", []) if isinstance(root, dict) else []
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        for c in ["STAT_CODE", "STAT_NAME"]:
            if c not in df.columns:
                df[c] = None
        return df[["STAT_CODE", "STAT_NAME"]].copy()

    @st.cache_data(show_spinner=False, ttl=60 * 60)
    def _ecos_item_list(stat_code: str) -> tuple[pd.DataFrame, str]:
        url = f"{BASE}/StatisticItemList/{ecos_key}/json/kr/1/2000/{stat_code}/"
        j = _ecos_get_json(url)
        root = j.get("StatisticItemList", {})
        rows = root.get("row", []) if isinstance(root, dict) else []
        if not rows:
            code, msg = _result_code_msg(j)
            return (pd.DataFrame(), f"StatisticItemList 실패 | stat={stat_code} | CODE={code} | MSG={msg}")
        df = pd.DataFrame(rows)
        for c in ["ITEM_CODE", "ITEM_NAME", "CYCLE"]:
            if c not in df.columns:
                df[c] = None
        return (df[["ITEM_CODE", "ITEM_NAME", "CYCLE"]].copy(), "")

    def _find_item_code(items_df: pd.DataFrame, must_keywords: list[str]) -> str:
        if items_df is None or items_df.empty:
            return ""
        sname = items_df["ITEM_NAME"].astype(str)
        mask = pd.Series(True, index=items_df.index)
        for kw in must_keywords:
            mask &= sname.str.contains(str(kw), na=False)
        hit = items_df[mask]
        return "" if hit.empty else str(hit.iloc[0]["ITEM_CODE"])

    def _cycle_for_item(items_df: pd.DataFrame, item_code: str, fallback: str = "D") -> str:
        if items_df is None or items_df.empty or not item_code:
            return fallback
        hit = items_df[items_df["ITEM_CODE"].astype(str) == str(item_code)]
        if hit.empty:
            return fallback
        c = str(hit.iloc[0].get("CYCLE", "")).strip()
        return c if c else fallback

    @st.cache_data(show_spinner=False, ttl=60 * 20)
    def _ecos_series(stat_code: str, cycle: str, start_yyyymmdd: str, end_yyyymmdd: str, item_code: str) -> pd.DataFrame:
        if not item_code:
            return pd.DataFrame()
        url = f"{BASE}/StatisticSearch/{ecos_key}/json/kr/1/2000/{stat_code}/{cycle}/{start_yyyymmdd}/{end_yyyymmdd}/{item_code}/"
        j = _ecos_get_json(url)
        root = j.get("StatisticSearch", {})
        rows = root.get("row", []) if isinstance(root, dict) else []
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        if ("TIME" not in df.columns) or ("DATA_VALUE" not in df.columns):
            return pd.DataFrame()
        df["date"] = pd.to_datetime(df["TIME"].astype(str), errors="coerce")
        df["value"] = pd.to_numeric(df["DATA_VALUE"], errors="coerce")
        df = df.dropna(subset=["date", "value"]).sort_values("date")
        return df[["date", "value"]].set_index("date")

    def _last_and_prev(df: pd.DataFrame):
        if df is None or df.empty:
            return (None, None, None)
        v = float(df["value"].iloc[-1])
        d = df.index[-1]
        pv = float(df["value"].iloc[-2]) if len(df) >= 2 else None
        return (d, v, pv)

    def _fetch_latest(stat_code: str, cycle: str, item_code: str) -> pd.DataFrame:
        end_dt = _now_kst().date()
        start_dt = end_dt - timedelta(days=120)
        s = start_dt.strftime("%Y%m%d")
        e = end_dt.strftime("%Y%m%d")
        return _ecos_series(stat_code, cycle, s, e, item_code)

    def _fetch_yearly_range(stat_code: str, cycle: str, item_code: str, years: list[int]) -> pd.DataFrame:
        out = []
        for y in years:
            s = f"{y}0101"
            e = f"{y}1231"
            df = _ecos_series(stat_code, cycle, s, e, item_code)
            if df is not None and not df.empty:
                out.append(df)
        if not out:
            return pd.DataFrame()
        return pd.concat(out).sort_index()

    # =========================
    # 1) 통계표 선택 UI를 "항상" 보여주기 (사라지는 문제 해결)
    # =========================
    tbl = _ecos_table_list()
    if tbl.empty:
        st.error("StatisticTableList 조회 실패 (인증키/네트워크 확인)")
        return

    # 기본값: 네 캡처에서 회사채가 잘 나오는 일별 테이블(817Y002)
    if "bond_gov_stat" not in st.session_state:
        st.session_state.bond_gov_stat = "817Y002"
    if "bond_corp_stat" not in st.session_state:
        st.session_state.bond_corp_stat = "817Y002"  # ✅ 회사채도 일별 테이블에 들어있는 케이스가 많아 기본 동일하게

    # 후보를 보기 좋게: 시장금리/일별/월/분기/년 포함된 것 위주로
    cand = tbl[tbl["STAT_NAME"].astype(str).str.contains("시장금리", na=False)].copy()
    if cand.empty:
        cand = tbl.copy()

    cand["label"] = cand["STAT_CODE"].astype(str) + " | " + cand["STAT_NAME"].astype(str)
    labels = cand["label"].tolist()

    st.markdown('<div class="section-title">⚙️ 통계표 선택</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        pick_gov = st.selectbox(
            "국고/통안 통계표(STAT_CODE)",
            labels,
            index=labels.index(next(x for x in labels if x.startswith(st.session_state.bond_gov_stat))) if any(x.startswith(st.session_state.bond_gov_stat) for x in labels) else 0,
            key="pick_gov_stat"
        )
        st.session_state.bond_gov_stat = pick_gov.split("|")[0].strip()

    with c2:
        pick_corp = st.selectbox(
            "회사채 통계표(STAT_CODE)",
            labels,
            index=labels.index(next(x for x in labels if x.startswith(st.session_state.bond_corp_stat))) if any(x.startswith(st.session_state.bond_corp_stat) for x in labels) else 0,
            key="pick_corp_stat"
        )
        st.session_state.bond_corp_stat = pick_corp.split("|")[0].strip()

    GOV_STAT = st.session_state.bond_gov_stat
    CORP_STAT = st.session_state.bond_corp_stat

    # 안내: 월/분기/년 테이블은 회사채(AA-/BBB-)가 없을 수 있음
    if "월" in pick_corp or "분기" in pick_corp or "년" in pick_corp:
        st.info("참고: '월/분기/년' 통계표에는 회사채(AA-, BBB-) 항목이 없거나 코드/명칭이 달라서 안 나올 수 있어요. 회사채는 보통 '일별' 통계표에서 잘 잡힙니다.")

    # =========================
    # 2) ItemList 로드
    # =========================
    gov_items, gov_err = _ecos_item_list(GOV_STAT)
    corp_items, corp_err = _ecos_item_list(CORP_STAT)

    if gov_items.empty:
        st.error(f"국고/통안 항목리스트 조회 실패: {gov_err}")
        return

    if corp_items.empty:
        st.warning("⚠️ 회사채 항목리스트 조회 실패")
        st.caption(corp_err)
        # 회사채만 비어도 국고/통안은 계속 보여주되, 회사채는 빈값 처리로 진행

    # =========================
    # 3) 6개 지표 item code 찾기
    # =========================
    code_msb1y  = _find_item_code(gov_items, ["통안", "1년"])
    code_ktb3y  = _find_item_code(gov_items, ["국고", "3년"])
    code_ktb5y  = _find_item_code(gov_items, ["국고", "5년"])
    code_ktb10y = _find_item_code(gov_items, ["국고", "10년"])

    gov_cycle_msb1y  = _cycle_for_item(gov_items, code_msb1y, "D")
    gov_cycle_ktb3y  = _cycle_for_item(gov_items, code_ktb3y, "D")
    gov_cycle_ktb5y  = _cycle_for_item(gov_items, code_ktb5y, "D")
    gov_cycle_ktb10y = _cycle_for_item(gov_items, code_ktb10y, "D")

    # 회사채: corp_items가 비면 빈 코드로 진행
    if corp_items.empty:
        code_aa3y, code_bbb3y = "", ""
        corp_cycle_aa3y, corp_cycle_bbb3y = "D", "D"
    else:
        # 같은 일별 테이블(817Y002)에서 회사채가 잡히는 캡처 케이스가 있으니, 그쪽에서 키워드로 찾음
        code_aa3y = _find_item_code(corp_items, ["회사채", "AA", "3년"]) or _find_item_code(corp_items, ["AA", "3년"])
        code_bbb3y = _find_item_code(corp_items, ["회사채", "BBB", "3년"]) or _find_item_code(corp_items, ["BBB", "3년"])
        corp_cycle_aa3y  = _cycle_for_item(corp_items, code_aa3y, "D")
        corp_cycle_bbb3y = _cycle_for_item(corp_items, code_bbb3y, "D")

    # =========================
    # 4) 최신 수익률(항상 최신)
    # =========================
    msb_latest   = _fetch_latest(GOV_STAT,  gov_cycle_msb1y,  code_msb1y)
    ktb3_latest  = _fetch_latest(GOV_STAT,  gov_cycle_ktb3y,  code_ktb3y)
    ktb5_latest  = _fetch_latest(GOV_STAT,  gov_cycle_ktb5y,  code_ktb5y)
    ktb10_latest = _fetch_latest(GOV_STAT,  gov_cycle_ktb10y, code_ktb10y)

    aa_latest    = _fetch_latest(CORP_STAT, corp_cycle_aa3y,  code_aa3y) if code_aa3y else pd.DataFrame()
    bbb_latest   = _fetch_latest(CORP_STAT, corp_cycle_bbb3y, code_bbb3y) if code_bbb3y else pd.DataFrame()

    def _latest_row(name: str, df: pd.DataFrame):
        d, v, pv = _last_and_prev(df)
        if v is None:
            return {"지표": name, "최신일": "-", "수익률(%)": np.nan, "전일대비(bp)": np.nan}
        chg_bp = (v - pv) * 100 if (pv is not None) else np.nan
        return {"지표": name, "최신일": d.strftime("%Y-%m-%d"), "수익률(%)": round(v, 3),
                "전일대비(bp)": (round(chg_bp, 1) if np.isfinite(chg_bp) else np.nan)}

    latest_df = pd.DataFrame([
        _latest_row("국고채(10년)", ktb10_latest),
        _latest_row("국고채(3년)", ktb3_latest),
        _latest_row("국고채(5년)", ktb5_latest),
        _latest_row("통안증권(1년)", msb_latest),
        _latest_row("회사채(3년, AA-)", aa_latest),
        _latest_row("회사채(3년, BBB-)", bbb_latest),
    ])

    st.markdown('<div class="section-title">📌 최신 수익률</div>', unsafe_allow_html=True)
    st.dataframe(latest_df, use_container_width=True, hide_index=True)

    # =========================
    # 5) 조회기간(3/5/10년) + 연도별 데이터/평균
    # =========================
    st.markdown('<div class="section-title">🕒 조회기간(연도별 데이터)</div>', unsafe_allow_html=True)
    years_sel = st.selectbox("조회 기간", ["3년", "5년", "10년"], index=0, key="bond_hist_years")
    n_years = int(years_sel.replace("년", ""))
    this_year = _now_kst().year
    years = list(range(this_year - (n_years - 1), this_year + 1))

    msb_hist   = _fetch_yearly_range(GOV_STAT,  gov_cycle_msb1y,  code_msb1y, years)
    ktb3_hist  = _fetch_yearly_range(GOV_STAT,  gov_cycle_ktb3y,  code_ktb3y, years)
    ktb5_hist  = _fetch_yearly_range(GOV_STAT,  gov_cycle_ktb5y,  code_ktb5y, years)
    ktb10_hist = _fetch_yearly_range(GOV_STAT,  gov_cycle_ktb10y, code_ktb10y, years)
    aa_hist    = _fetch_yearly_range(CORP_STAT, corp_cycle_aa3y,  code_aa3y, years) if code_aa3y else pd.DataFrame()
    bbb_hist   = _fetch_yearly_range(CORP_STAT, corp_cycle_bbb3y, code_bbb3y, years) if code_bbb3y else pd.DataFrame()

    series_map = {
        "통안증권(1년)": msb_hist,
        "국고채(3년)": ktb3_hist,
        "국고채(5년)": ktb5_hist,
        "국고채(10년)": ktb10_hist,
        "회사채(3년, AA-)": aa_hist,
        "회사채(3년, BBB-)": bbb_hist,
    }

    long_rows = []
    for name, sdf in series_map.items():
        if sdf is None or sdf.empty:
            continue
        tmp = sdf.copy()
        tmp["지표"] = name
        tmp["년도"] = tmp.index.year
        long_rows.append(tmp.reset_index().rename(columns={"date": "일자"}))

    if not long_rows:
        st.warning("선택한 조회기간에 표시할 데이터가 없습니다.")
        return

    long_df = pd.concat(long_rows, ignore_index=True)
    if "일자" not in long_df.columns and "date" in long_df.columns:
        long_df = long_df.rename(columns={"date": "일자"})
    long_df["일자"] = pd.to_datetime(long_df["일자"], errors="coerce")
    long_df = long_df.dropna(subset=["일자"])
    long_df["년도"] = long_df["일자"].dt.year

    st.markdown('<div class="section-title">📚 연도별 데이터</div>', unsafe_allow_html=True)
    years_desc = sorted(long_df["년도"].unique(), reverse=True)
    for y in years_desc:
        with st.expander(f"{y}년 데이터 보기", expanded=(y == years_desc[0])):
            ydf = long_df[long_df["년도"] == y].copy()
            pivot = ydf.pivot_table(index="일자", columns="지표", values="value", aggfunc="last").sort_index()
            pivot = pivot.reset_index()
            pivot["일자"] = pivot["일자"].dt.strftime("%Y-%m-%d")
            st.dataframe(pivot, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">📊 연도별 평균(%)</div>', unsafe_allow_html=True)
    avg_df = (
        long_df.groupby(["년도", "지표"])["value"]
        .mean()
        .reset_index()
        .pivot(index="년도", columns="지표", values="value")
        .sort_index(ascending=False)
        .round(3)
        .reset_index()
    )
    st.dataframe(avg_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">📈 추이</div>', unsafe_allow_html=True)
    pick = st.selectbox("차트로 볼 지표", list(series_map.keys()), index=0, key="bond_chart_pick")
    sdf = series_map.get(pick, pd.DataFrame())
    if sdf is None or sdf.empty:
        st.warning("선택한 지표의 데이터가 없습니다.")
        return

    plot_df = sdf.reset_index().rename(columns={"date": "일자"})
    if "일자" not in plot_df.columns and "index" in plot_df.columns:
        plot_df = plot_df.rename(columns={"index": "일자"})
    plot_df["일자"] = pd.to_datetime(plot_df["일자"], errors="coerce")
    plot_df = plot_df.dropna(subset=["일자", "value"])

    years_ticks = sorted(plot_df["일자"].dt.year.unique().tolist())
    tick_values = [pd.Timestamp(f"{y}-01-01") for y in years_ticks]

    chart = (
        alt.Chart(plot_df)
        .mark_line()
        .encode(
            x=alt.X("일자:T", axis=alt.Axis(values=tick_values, format="%Y", labelAngle=0, title=None)),
            y=alt.Y("value:Q", title="수익률(%)"),
        )
        .properties(height=320)
    )
    st.altair_chart(chart, use_container_width=True)




def render_home():
    st.markdown(
        """
        <div class="card">
          <div style="font-size:18px;font-weight:950;letter-spacing:-0.3px;color:#0b1224;">📌 홈 대시보드</div>
          <div style="color:rgba(15,23,42,0.70);margin-top:6px;line-height:1.55;">
            홈은 <b>핵심 요약 + 시각화</b>만 제공합니다. (세부는 상단 탭에서 확인)
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    info = st.session_state.company_info or {}
    wide = st.session_state.wide
    unit = st.session_state.unit

    # -------------------------
    # Market data (robust)
    # -------------------------
    price_df = st.session_state.price_df
    market_ok = bool(st.session_state.market_ok) and (price_df is not None) and (not price_df.empty)

    # close/asof: session_state 값이 0/NaN이면 price_df 마지막 값으로 대체
    current_px = st.session_state.close if market_ok else None
    asof = st.session_state.mkt_date if market_ok else None

    if market_ok:
        closes = pd.to_numeric(price_df["Close"], errors="coerce").dropna()
        if not closes.empty:
            last_close = float(closes.iloc[-1])
            last_date = pd.to_datetime(price_df["Date"].iloc[-1]).strftime("%Y%m%d")
            if (current_px is None) or (not np.isfinite(current_px)) or (float(current_px) <= 0):
                current_px = last_close
            if (asof is None) or (str(asof).strip() == ""):
                asof = last_date

    # 52W High/Low & Position (clamp 0~100)
    hi52 = lo52 = pos52 = None
    if market_ok and (current_px is not None) and np.isfinite(current_px) and float(current_px) > 0:
        closes = pd.to_numeric(price_df["Close"], errors="coerce").dropna()
        if not closes.empty:
            hi52 = float(closes.max())
            lo52 = float(closes.min())
            if hi52 != lo52:
                pos52 = (float(current_px) - lo52) / (hi52 - lo52)
                pos52 = float(np.clip(pos52, 0.0, 1.0))

    # YTD return (if empty -> fallback to 1Y return)
   
    
    ytd = None
    ret_1y = None
    if market_ok:
        dfy = price_df.copy()
        dfy["Date"] = pd.to_datetime(dfy["Date"])
        closes = pd.to_numeric(dfy["Close"], errors="coerce")
        dfy["Close"] = closes
        dfy = dfy.dropna(subset=["Close"])
        dfy = dfy.sort_values("Date")

        if not dfy.empty:
            # 1Y (first vs last in the loaded window)
            p0 = float(dfy.iloc[0]["Close"])
            p1 = float(dfy.iloc[-1]["Close"])
            if p0 > 0:
                ret_1y = (p1 / p0) - 1

            # -----------------------------
            # YTD (KST 기준 통일 + 데이터 최소 2개 필요)
            # -----------------------------
            this_year = _now_kst().year  # ✅ 서버시간 대신 KST 기준으로 연도 통일
            y0 = dfy[dfy["Date"].dt.year == this_year].copy()

            if len(y0) >= 2:
                p0y = float(y0.iloc[0]["Close"])
                p1y = float(y0.iloc[-1]["Close"])
                if p0y > 0:
                    ytd = (p1y / p0y) - 1


    # -------------------------
    # Finance snapshot
    # -------------------------
    ratios, base = compute_fin_ratios(wide) if (wide is not None and not wide.empty) else ({}, {})
    rev = base.get("rev")
    op  = base.get("op")

    rev_yoy = op_yoy = opm_last = None
    if rev is not None:
        rev_yoy = pct_change(last_value(rev), prev_value(rev))
    if op is not None:
        op_yoy = pct_change(last_value(op), prev_value(op))
    if (rev is not None) and (op is not None):
        opm = (pd.to_numeric(op, errors="coerce") / pd.to_numeric(rev, errors="coerce")).replace([np.inf, -np.inf], np.nan)
        opm_last = last_value(opm)

    # -------------------------
    # KPI row (4 cards)
    # -------------------------
    st.write("")
    k1, k2, k3, k4 = st.columns(4)

    kpi(
        k1,
        "현재가",
        "-" if (current_px is None or not np.isfinite(current_px) or float(current_px) <= 0) else f"{float(current_px):,.0f} 원",
        sub=f"기준일: {asof}" if asof else "KRX 결측/휴장 가능"
    )

    if (hi52 is None) or (lo52 is None) or (pos52 is None):
        kpi(k2, "52주 위치", "-", sub="데이터 부족/현재가 결측")
    else:
        kpi(
            k2,
            "52주 위치",
            f"{pos52*100:,.0f}%",
            sub=f"Low {lo52:,.0f} ~ High {hi52:,.0f}"
        )

    # YTD first, fallback to 1Y
    if ytd is not None:
        kpi(k3, "YTD 수익률", f"{ytd*100:,.1f}%", sub="올해 첫 거래일 대비")
    else:
        kpi(k3, "최근 1년 수익률", "-" if ret_1y is None else f"{ret_1y*100:,.1f}%", sub="(YTD 데이터 없으면 1Y로 대체)")



    # Finance anchor (avoid nonsense when missing)
    txt = []
    if rev_yoy is not None and np.isfinite(rev_yoy):
        txt.append(f"매출 YoY {rev_yoy*100:,.1f}%")
    if opm_last is not None and np.isfinite(opm_last):
        txt.append(f"OPM {opm_last*100:,.1f}%")
    kpi(k4, "재무 핵심", " / ".join(txt) if txt else "-", sub="최근연도 기준")

    # -------------------------
    # Charts layout: Price full width, then 2 small charts side-by-side
    # -------------------------
    st.write("")
    st.markdown('<div class="section-title">📉 주가(최근 1년)</div>', unsafe_allow_html=True)
    if not market_ok:
        st.info("주가 데이터가 아직 준비되지 않았습니다. (왼쪽에서 ② 재무 가져오기 완료 필요)")
        if st.session_state.get("market_msg"):
            st.caption(f"시장데이터 메시지: {st.session_state.market_msg}")
    else:
        ch = alt_time_series(price_df, "Date", "Close", "Close", fmt=",.0f", color=COLOR["price"])
        st.altair_chart(ch, use_container_width=True)


    st.write("")
    a1, a2 = st.columns(2)
    with a1:
        st.markdown('<div class="section-title">📈 매출(또는 수익)</div>', unsafe_allow_html=True)
        if rev is None:
            st.info("매출 계정이 부족합니다.")
        else:
            st.altair_chart(alt_line_chart(rev, unit, is_ratio=False, color=COLOR["rev"], height=220), use_container_width=True)

    with a2:
        st.markdown('<div class="section-title">📈 영업이익률(OPM)</div>', unsafe_allow_html=True)
        if (rev is None) or (op is None):
            st.info("영업이익/매출 계정이 부족합니다.")
        else:
            opm = (pd.to_numeric(op, errors="coerce") / pd.to_numeric(rev, errors="coerce")).replace([np.inf, -np.inf], np.nan)
            st.altair_chart(alt_line_chart(opm, unit, is_ratio=True, color=COLOR["margin"], height=220), use_container_width=True)

    # -------------------------
    # Executive notes (numbers-based, short)
    # -------------------------
    st.write("")
    st.markdown('<div class="section-title">🧠 한줄 진단(숫자 기반)</div>', unsafe_allow_html=True)

    notes = []
    if rev_yoy is not None:
        notes.append(f"매출 YoY: **{rev_yoy*100:.1f}%** (증가/감소 원인을 단가·물량·인식타이밍으로 분해)")
    if op_yoy is not None:
        notes.append(f"영업이익 YoY: **{op_yoy*100:.1f}%** (원가·고정비 레버리지·일회성 여부 확인)")
    if opm_last is not None:
        notes.append(f"OPM: **{opm_last*100:.1f}%** (지속 가능성: 믹스·원가구조·환율 영향 점검)")
    if (notes == []):
        notes = ["재무 데이터가 부족해 요약을 만들 수 없습니다. 왼쪽에서 ② 재무 가져오기를 먼저 완료하세요."]

    render_commentary_box(
        "Executive Summary",
        notes[:5],
        badges=[("홈은 요약", "info")]
    )


def render_major_table(wide, year_to_term, unit):
    st.markdown('<div class="section-title">🧾 주요 재무계정</div>', unsafe_allow_html=True)
    wide_disp = prepare_table_display(wide, year_to_term, unit)
    if wide_disp.empty:
        st.warning("주요 재무계정 데이터가 비어있습니다.")
        return False
    st.dataframe(wide_disp, use_container_width=True, height=df_height(wide_disp, max_rows=len(wide_disp)))
    return True

def render_is_major_table(wide_is: pd.DataFrame, year_to_term: dict, unit: str):
    st.markdown('<div class="section-title">🧾 손익계산서(IS)</div>', unsafe_allow_html=True)

    if wide_is is None or wide_is.empty:
        st.warning("IS 데이터가 비어있습니다. (DART 전체계정 매칭 실패/결측 가능)")
        return False

    cols = ["매출", "원가", "매출총이익", "판관비", "영업이익","영업외수익", "영업외비용", "영업외손익(수익-비용)","법인세", "당기순이익"]

    src = wide_is.copy()
    for c in cols:
        if c not in src.columns:
            src[c] = np.nan
    src = src[cols]

    # 표는 '행=계정, 열=연도'로
    view = add_year_term_index(src, year_to_term)
    t = view  # rows: 계정, cols: 연도(기수)

    disp = pd.DataFrame(index=t.index, columns=t.columns)
    if is_trillion_mode(unit):
        t2 = t / 1_000_000_000_000
        for r in t2.index:
            disp.loc[r] = pd.to_numeric(t2.loc[r], errors="coerce").map(lambda v: "" if pd.isna(v) else f"{float(v):,.3f}")
    else:
        for r in t.index:
            disp.loc[r] = pd.to_numeric(t.loc[r], errors="coerce").map(lambda v: "" if pd.isna(v) else f"{float(v):,.0f}")

    disp = clean_empty_rows_cols(disp)
    st.dataframe(disp, use_container_width=True, height=df_height(disp, max_rows=len(disp)))
    return True


def render_core_charts_peer(wide, unit, title: str | None = None):
    """
    Peer 탭용: '핵심 지표 추이' 5개 그래프만 출력 (타이틀은 선택)
    """
    if wide is None or getattr(wide, "empty", True):
        st.info("핵심 지표(손익) 데이터가 없습니다.")
        return

    if title:
        st.markdown(f'<div class="section-title">📈 {title}</div>', unsafe_allow_html=True)

    # IS wide(=wide_is) 기준 컬럼 우선 사용
    rev_s = wide["매출"] if ("매출" in wide.columns) else None
    cogs_s = wide["원가"] if ("원가" in wide.columns) else None
    op_s  = wide["영업이익"] if ("영업이익" in wide.columns) else None
    ni_s  = wide["당기순이익"] if ("당기순이익" in wide.columns) else None

    # fallback (기존 wide 구조일 때)
    if rev_s is None:
        _, rev_s = pick_by_alias(wide, "REV")
    if op_s is None:
        _, op_s = pick_by_alias(wide, "OP")
    if ni_s is None:
        _, ni_s = pick_by_alias(wide, "NI")

    # 영업이익률
    opm_s = None
    if (rev_s is not None) and (op_s is not None):
        opm_s = pd.to_numeric(op_s, errors="coerce") / pd.to_numeric(rev_s, errors="coerce")

    # 원가율(원가/매출)
    cogs_ratio = None
    if (rev_s is not None) and (cogs_s is not None):
        cogs_ratio = pd.to_numeric(cogs_s, errors="coerce") / pd.to_numeric(rev_s, errors="coerce")

    # ✅ 요청대로: 매출, 원가율, 영업이익, 영업이익률, 순이익 (5개)
    g1, g2, g3, g4, g5 = st.columns(5)
    with g1:
        render_plain_chart("매출(또는 수익)", alt_line_chart(rev_s, unit, is_ratio=False, color=COLOR["rev"], height=220))
    with g2:
        render_plain_chart("원가율(원가/매출)", alt_line_chart(cogs_ratio, unit, is_ratio=True, color="#fb7185", height=220))
    with g3:
        render_plain_chart("영업이익", alt_line_chart(op_s, unit, is_ratio=False, color=COLOR["op"], height=220))
    with g4:
        render_plain_chart("영업이익률", alt_line_chart(opm_s, unit, is_ratio=True, color=COLOR["margin"], height=220))
    with g5:
        render_plain_chart("순이익", alt_line_chart(ni_s, unit, is_ratio=False, color=COLOR["ni"], height=220))


def render_bs_history_only(wide, year_to_term, unit, title: str | None = None):
    """
    Peer 탭용: BS 히스토리 표만 출력 (render_bs의 '첫 표' 부분만 분리)
    """
    if wide is None or getattr(wide, "empty", True):
        st.info("BS 데이터가 없습니다.")
        return

    if title:
        st.markdown(f'<div class="section-title">📦 {title}</div>', unsafe_allow_html=True)

    cols = {}
    for key, alias_key in [
        ("자산총계", "ASSET"),
        ("부채총계", "LIAB"),
        ("자본총계", "EQUITY"),
        ("유동자산", "CA"),
        ("유동부채", "CL"),
        ("비유동자산", "NCA"),
        ("비유동부채", "NCL"),
        ("자본금", "CAPITAL"),
    ]:
        if wide is not None and key in wide.columns:
            cols[key] = pd.to_numeric(wide[key], errors="coerce")
        else:
            _, s = pick_by_alias(wide, alias_key)
            if s is not None:
                cols[key] = pd.to_numeric(s, errors="coerce")

    if not cols:
        st.warning("BS 핵심 계정이 부족합니다.")
        return

    bs = pd.DataFrame(cols)
    if ("유동자산" in bs.columns) and ("유동부채" in bs.columns):
        bs["NWC(유동자산-유동부채)"] = bs["유동자산"] - bs["유동부채"]

    bs = add_year_term_index(bs, year_to_term)

    # display formatting
    if is_trillion_mode(unit):
        bs2 = bs / 1_000_000_000_000
        disp = pd.DataFrame(index=bs2.index)
        for c in bs2.columns:
            disp[c] = pd.to_numeric(bs2[c], errors="coerce").map(lambda v: "" if pd.isna(v) else f"{float(v):,.3f}")
    else:
        disp = pd.DataFrame(index=bs.index)
        for c in bs.columns:
            disp[c] = pd.to_numeric(bs[c], errors="coerce").map(lambda v: "" if pd.isna(v) else f"{float(v):,.0f}")

    disp = clean_empty_rows_cols(disp)
    st.dataframe(disp, use_container_width=True, height=df_height(disp, max_rows=len(disp)))


def render_is(wide, year_to_term, unit, industry_tag):
    wide_is = st.session_state.get("wide_is", None)
    use_df = wide_is if (wide_is is not None and not wide_is.empty) else wide
    
    ok = render_is_major_table(use_df, year_to_term, unit)
    if not ok:
        return

    render_core_charts_peer(use_df, unit)

    st.markdown('<div class="section-title">📝 손익(IS) 코멘터리</div>', unsafe_allow_html=True)
    # 코멘터리는 기존 로직 유지(REV/OP/NI 기반)
    bullets, badges = build_is_commentary(wide, industry_tag)
    render_commentary_box("손익(IS) 해석", bullets, badges)



def render_bs(wide, year_to_term, unit, industry_tag):
    # ✅ 1) 표(히스토리) 먼저: 제목에서 (주요) 제거 + 항목 확장
    st.markdown('<div class="section-title">📦 BS 히스토리</div>', unsafe_allow_html=True)

    cols = {}
    for key, alias_key in [
        ("자산총계", "ASSET"),
        ("부채총계", "LIAB"),
        ("자본총계", "EQUITY"),
        ("유동자산", "CA"),
        ("유동부채", "CL"),
        ("비유동자산", "NCA"),
        ("비유동부채", "NCL"),
        ("자본금", "CAPITAL"),
    ]:
        if wide is not None and key in wide.columns:
            cols[key] = pd.to_numeric(wide[key], errors="coerce")
        else:
            _, s = pick_by_alias(wide, alias_key)
            if s is not None:
                cols[key] = pd.to_numeric(s, errors="coerce")

    if not cols:
        st.warning("BS 핵심 계정이 부족합니다.")
        return

    bs = pd.DataFrame(cols)
    if ("유동자산" in bs.columns) and ("유동부채" in bs.columns):
        bs["NWC(유동자산-유동부채)"] = bs["유동자산"] - bs["유동부채"]

    bs = add_year_term_index(bs, year_to_term)

    # display formatting
    if is_trillion_mode(unit):
        bs2 = bs / 1_000_000_000_000
        disp = pd.DataFrame(index=bs2.index)
        for c in bs2.columns:
            disp[c] = pd.to_numeric(bs2[c], errors="coerce").map(lambda v: "" if pd.isna(v) else f"{float(v):,.3f}")
    else:
        disp = pd.DataFrame(index=bs.index)
        for c in bs.columns:
            disp[c] = pd.to_numeric(bs[c], errors="coerce").map(lambda v: "" if pd.isna(v) else f"{float(v):,.0f}")

    disp = clean_empty_rows_cols(disp)
    st.dataframe(disp, use_container_width=True, height=df_height(disp, max_rows=len(disp)))

    

    # =========================================================
    # ✅ 1-5) 운전자본 회전율(AR/INV/AP) 표 + 그래프 (BS 히스토리 아래)
    # =========================================================
    st.markdown('<div class="section-title">🔄 운전자본 회전율(AR/INV/AP)</div>', unsafe_allow_html=True)
    st.caption("회전율 = 손익계정(매출/원가) ÷ (해당 BS 항목의 평균잔액). 평균잔액은 (당기+전기)/2로 근사합니다.")

    # ---- 1) 필요한 시계열(AR/INV/AP, 매출/원가) 뽑기
    # BS 항목: wide(주요재무 wide)에서 alias로 찾음
    wc_bs = st.session_state.get("wc_bs", None)

    ar = inv = ap = None
    if wc_bs is not None and not wc_bs.empty:
        ar  = pd.to_numeric(wc_bs.get("AR"),  errors="coerce")
        inv = pd.to_numeric(wc_bs.get("INV"), errors="coerce")
        ap  = pd.to_numeric(wc_bs.get("AP"),  errors="coerce")


    def has_value(s):
        return s is not None and pd.to_numeric(s, errors="coerce").dropna().size > 0


    # IS 항목: wide_is(재구성된 IS)가 있으면 그걸 최우선 사용
    wide_is_local = st.session_state.get("wide_is", None)
    rev_s = None
    cogs_s = None

    if wide_is_local is not None and not wide_is_local.empty:
        if "매출" in wide_is_local.columns:
            rev_s = pd.to_numeric(wide_is_local["매출"], errors="coerce")
        if "원가" in wide_is_local.columns:
            cogs_s = pd.to_numeric(wide_is_local["원가"], errors="coerce")

    # fallback: 기존 wide에서 alias로
    if rev_s is None:
        _, tmp = pick_by_alias(wide, "REV")
        rev_s = pd.to_numeric(tmp, errors="coerce") if tmp is not None else None
    if cogs_s is None:
        _, tmp = pick_by_alias(wide, "COGS")
        cogs_s = pd.to_numeric(tmp, errors="coerce") if tmp is not None else None

    # ---- 2) 최소 요건 체크
    need_any = has_value(ar) or has_value(inv) or has_value(ap)

    has_rev  = has_value(rev_s)
    has_cogs = has_value(cogs_s)

    if ((not has_rev) and (not has_cogs)) or (not need_any):
        st.info("회전율 계산에 필요한 계정이 부족합니다. (매출/원가 + AR/재고/AP 중 일부가 필요)")
        return
    else:
        # ---- 3) 계산용 DataFrame(연도 index는 wide index와 동일하게 맞춤)
        # wide index가 연도(정수)라 가정. 혹시 문자열이어도 처리.
        idx = None
        for s in [rev_s, cogs_s, ar, inv, ap]:
            if s is not None and hasattr(s, "index"):
                idx = s.index
                break
        df_turn = pd.DataFrame(index=idx)

        if rev_s is not None:
            df_turn["매출"] = rev_s
        if cogs_s is not None:
            df_turn["원가"] = cogs_s
        if ar is not None:
            df_turn["매출채권(AR)"] = ar
        if inv is not None:
            df_turn["재고자산(INV)"] = inv
        if ap is not None:
            df_turn["매입채무(AP)"] = ap

        # 연도 정렬(오름차순)로 평균잔액 계산 후 다시 내림차순 표기
        df_turn = df_turn.copy()
        try:
            df_turn.index = df_turn.index.astype(int)
        except Exception:
            pass
        df_turn = df_turn.sort_index(ascending=True)

        # 평균잔액 = (당기 + 전기) / 2
        def avg_balance(col):
            if col not in df_turn.columns:
                return None
            return (df_turn[col] + df_turn[col].shift(1)) / 2

        ar_avg  = avg_balance("매출채권(AR)")
        inv_avg = avg_balance("재고자산(INV)")
        ap_avg  = avg_balance("매입채무(AP)")

        # 회전율
        # AR Turnover = 매출 / avg AR
        if (rev_s is not None) and (ar_avg is not None):
            df_turn["AR 회전율(회)"] = df_turn["매출"] / ar_avg
            df_turn["DSO(일)"] = 365 / df_turn["AR 회전율(회)"]

        # Inventory Turnover = 원가 / avg INV (원가 없으면 매출로 대체는 왜곡 가능 → 원가 없으면 계산 보류)
        if (cogs_s is not None) and (inv_avg is not None):
            df_turn["재고 회전율(회)"] = df_turn["원가"] / inv_avg
            df_turn["DIO(일)"] = 365 / df_turn["재고 회전율(회)"]

        # AP Turnover = 원가 / avg AP
        if (cogs_s is not None) and (ap_avg is not None):
            df_turn["AP 회전율(회)"] = df_turn["원가"] / ap_avg
            df_turn["DPO(일)"] = 365 / df_turn["AP 회전율(회)"]

        # CCC = DSO + DIO - DPO (가능한 항목만)
        if ("DSO(일)" in df_turn.columns) and ("DIO(일)" in df_turn.columns) and ("DPO(일)" in df_turn.columns):
            df_turn["CCC(일)"] = df_turn["DSO(일)"] + df_turn["DIO(일)"] - df_turn["DPO(일)"]

        # 보기 좋게(내림차순)
        df_turn = df_turn.sort_index(ascending=False)

        # ---- 4) 표(상세 수치)
        show_cols = []
        for c in ["매출", "원가", "매출채권(AR)", "재고자산(INV)", "매입채무(AP)",
                  "AR 회전율(회)", "DSO(일)", "재고 회전율(회)", "DIO(일)", "AP 회전율(회)", "DPO(일)", "CCC(일)"]:
            if c in df_turn.columns:
                show_cols.append(c)

        table = df_turn[show_cols].copy()

        # 포맷팅(표시용)
        disp_turn = pd.DataFrame(index=table.index)
        for c in table.columns:
            s = pd.to_numeric(table[c], errors="coerce")
            if c in ["AR 회전율(회)", "재고 회전율(회)", "AP 회전율(회)"]:
                disp_turn[c] = s.map(lambda v: "" if pd.isna(v) else f"{float(v):,.2f}")
            elif c in ["DSO(일)", "DIO(일)", "DPO(일)", "CCC(일)"]:
                disp_turn[c] = s.map(lambda v: "" if pd.isna(v) else f"{float(v):,.0f}")
            else:
                # 금액
                if is_trillion_mode(unit):
                    disp_turn[c] = s.map(lambda v: "" if pd.isna(v) else f"{float(v)/1e12:,.3f}")
                else:
                    disp_turn[c] = s.map(lambda v: "" if pd.isna(v) else f"{float(v):,.0f}")

        disp_turn = clean_empty_rows_cols(disp_turn)
        st.dataframe(disp_turn, use_container_width=True, height=df_height(disp_turn, max_rows=len(disp_turn)))

        # ---- 5) 그래프(회전율)
        # Altair 멀티라인(AR/INV/AP 회전율)
        plot_cols = [c for c in ["AR 회전율(회)", "재고 회전율(회)", "AP 회전율(회)"] if c in df_turn.columns]
        if len(plot_cols) >= 1:
            plot_df = df_turn[plot_cols].copy()
            plot_df = plot_df.reset_index()
            plot_df = plot_df.rename(columns={plot_df.columns[0]: "Year"})
            plot_df = plot_df.melt(id_vars=["Year"], var_name="항목", value_name="회전율")

            try:
                plot_df["Year"] = plot_df["Year"].astype(int)
            except Exception:
                pass

            chart = (
                alt.Chart(plot_df.dropna())
                .mark_line(point=alt.OverlayMarkDef(filled=True, size=45))
                .encode(
                    x=alt.X("Year:O", title=None),
                    y=alt.Y("회전율:Q", title=None),
                    color=alt.Color("항목:N", title=None),
                    tooltip=[alt.Tooltip("Year:O", title="연도"),
                             alt.Tooltip("항목:N", title="항목"),
                             alt.Tooltip("회전율:Q", title="회전율", format=",.2f")]
                )
                .properties(height=260)
            )
            st.altair_chart(chart, use_container_width=True)
            
            
            # ---- 6) 운전자본 회전율 해석 (그래프 아래 코멘트)
            st.markdown("#### 📌 운전자본 회전율 해석")

            comment_lines = []

            # AR
            if "AR 회전율(회)" in df_turn.columns:
                ar_trend = df_turn["AR 회전율(회)"].dropna().sort_index()
                if len(ar_trend) >= 2 and ar_trend.iloc[-1] >= ar_trend.iloc[-2]:
                    comment_lines.append(
                        "- **매출채권 회전율은 개선 흐름**을 보이고 있으며, 이는 매출 증가에도 불구하고 채권 회수 효율이 유지되고 있음을 의미한다."
                    )
                else:
                    comment_lines.append(
                        "- **매출채권 회전율은 다소 둔화**되고 있어, 매출 확대 국면에서 채권 회수 관리가 중요해질 수 있다."
                    )

            # Inventory
            if "재고 회전율(회)" in df_turn.columns:
                inv_trend = df_turn["재고 회전율(회)"].dropna().sort_index()
                if len(inv_trend) >= 2 and inv_trend.iloc[-1] >= inv_trend.iloc[-2]:
                    comment_lines.append(
                        "- **재고 회전율은 안정적인 수준**을 유지하고 있어 재고 관리 부담은 제한적인 것으로 판단된다."
                    )
                else:
                    comment_lines.append(
                        "- **재고 회전율의 변동성**이 확대되고 있어, 수요 변동에 따른 재고 관리 리스크 점검이 필요하다."
                    )

            # AP
            if "AP 회전율(회)" in df_turn.columns:
                ap_trend = df_turn["AP 회전율(회)"].dropna().sort_index()
                if len(ap_trend) >= 2 and ap_trend.iloc[-1] <= ap_trend.iloc[-2]:
                    comment_lines.append(
                        "- **매입채무 회전율은 낮은 수준**을 유지하고 있어, 거래처를 통한 운전자본 조달 구조가 유지되고 있다."
                    )
                else:
                    comment_lines.append(
                        "- **매입채무 회전율이 상승**하고 있어, 단기적으로 지급 조건 변화 여부에 대한 모니터링이 필요하다."
                    )

            # CCC
            if "CCC(일)" in df_turn.columns:
                ccc_trend = df_turn["CCC(일)"].dropna().sort_index()
                if len(ccc_trend) >= 2 and ccc_trend.iloc[-1] <= ccc_trend.iloc[-2]:
                    comment_lines.append(
                        "- **CCC는 전반적으로 안정적인 수준**을 유지하고 있어 현금 회수 구조에 큰 변화는 없는 것으로 판단된다."
                    )
                else:
                    comment_lines.append(
                        "- **CCC가 확대되는 추세**로, 운전자본 부담이 점진적으로 증가하고 있는지 점검이 필요하다."
                    )

            for line in comment_lines:
                st.markdown(line)
                
            if not comment_lines:
                st.info("해석할 회전율 항목(AR/재고/AP/CCC)이 없습니다. 컬럼명을 확인하세요.")    
           
        else:
            st.info("회전율 그래프를 만들 수 있는 항목이 없습니다.")




    # ✅ 2) 그래프(추가재무지표 전부 BS로 이동, 색 유지)
    st.markdown('<div class="section-title">📌 추가 재무지표</div>', unsafe_allow_html=True)

    ratios, _ = compute_fin_ratios(wide)
    roe = ratios.get("ROE")
    roa = ratios.get("ROA")
    de = ratios.get("Debt_to_Equity")
    cr = ratios.get("Current_Ratio")
    ncar = ratios.get("NonCurrent_Asset_Ratio")

    a1, a2, a3, a4, a5 = st.columns(5)
    with a1:
        render_plain_chart("ROE", alt_line_chart(roe, unit, is_ratio=True, color=COLOR["ratio1"], height=220))
    with a2:
        render_plain_chart("ROA", alt_line_chart(roa, unit, is_ratio=True, color=COLOR["ratio2"], height=220))
    with a3:
        render_plain_chart("부채/자본(D/E)", alt_line_chart(de, unit, is_ratio=True, color=COLOR["ratio3"], height=220))
    with a4:
        render_plain_chart("유동비율(Current Ratio)", alt_line_chart(cr, unit, is_ratio=True, color=COLOR["ratio1"], height=220))
    with a5:
        render_plain_chart("비유동비율(비유동자산/자본)", alt_line_chart(ncar, unit, is_ratio=True, color=COLOR["ratio2"], height=220))

    # ✅ 3) 코멘터리(마지막)
    st.markdown('<div class="section-title">📦 재무상태(BS) 코멘터리</div>', unsafe_allow_html=True)
    bullets, badges = build_bs_commentary(wide, industry_tag)
    render_commentary_box("재무상태(BS) 해석", bullets, badges)




def render_market_page(info: dict, wide: pd.DataFrame, evhist: pd.DataFrame):
    st.markdown('<div class="section-title">📌 시장데이터 · 멀티플 (KRX)</div>', unsafe_allow_html=True)
    st.caption("KRX(pykrx) 기반으로 주가 조회 & 발행주식수에 따라 시총,PER,PBR,EPS,BSP 계산 (휴장일은 자동으로 과거 영업일로 롤백)")

    price_df = st.session_state.price_df
    market_ok = bool(st.session_state.market_ok) and (price_df is not None) and (not price_df.empty)
    if not market_ok:
        st.warning("시장데이터가 준비되지 않았습니다. (왼쪽에서 ② 재무 가져오기를 다시 시도)")
        if st.session_state.market_msg:
            st.caption(st.session_state.market_msg)
        return

    # -------------------------
    # 기준값(주가/일자)
    # -------------------------
    close = st.session_state.close
    asof = st.session_state.mkt_date

    try:
        closes = pd.to_numeric(price_df["Close"], errors="coerce").dropna()
        if (close is None) and (not closes.empty):
            close = float(closes.iloc[-1])
        if (asof is None) and ("Date" in price_df.columns) and (not price_df.empty):
            asof = pd.to_datetime(price_df["Date"].iloc[-1]).strftime("%Y%m%d")
    except Exception:
        pass

    # -------------------------
    # 사용자 수동 입력: 발행주식수(우선 적용)
    # -------------------------
    st.markdown("### 발행주식수(수동 입력, 선택)")
    default_shares = st.session_state.shares if st.session_state.shares is not None else 0.0
    manual_shares = st.number_input(
        "발행주식수(주) — 직접 입력하면 시총/EPS/BPS/PER/PBR/EV·배수 계산에 우선 반영됩니다.",
        value=float(default_shares) if default_shares is not None else 0.0,
        step=1.0,
        format="%.0f",
        key="mkt_manual_shares",
    )

    manual_override = (manual_shares is not None) and np.isfinite(float(manual_shares)) and (float(manual_shares) > 0)
    shares_eff = float(manual_shares) if manual_override else st.session_state.shares

    # -------------------------
    # 시총(우선: 수동입력 시 close*shares / 그 외 KRX 조회값 / fallback: close*shares)
    # -------------------------
    mktcap_eff = st.session_state.mktcap

    if manual_override and (close is not None) and (shares_eff is not None) and np.isfinite(close) and np.isfinite(shares_eff):
        try:
            mktcap_eff = float(close) * float(shares_eff)
        except Exception:
            mktcap_eff = None

    if (mktcap_eff is None) and (close is not None) and (shares_eff is not None) and np.isfinite(close) and np.isfinite(shares_eff):
        try:
            mktcap_eff = float(close) * float(shares_eff)
        except Exception:
            mktcap_eff = None

    # -------------------------
    # 재무(우선: KRX 펀더멘털 / fallback: DART 기반 내부 계산)
    #   - 단, 수동 주식수 입력 시 EPS/BPS/PER/PBR은 "수동 주식수" 기준으로 재계산(가능하면)
    # -------------------------
    fund = st.session_state.fund or {}
    per_krx = _to_num(fund.get("PER"))
    pbr_krx = _to_num(fund.get("PBR"))
    eps_krx = _to_num(fund.get("EPS"))
    bps_krx = _to_num(fund.get("BPS"))
    f_asof = fund.get("date") or asof

    # DART fallback(연간 기준): EPS = NI / shares, BPS = Equity / shares
    ni_last = None
    eq_last = None
    try:
        if wide is not None and not wide.empty:
            # NI
            if ("당기순이익" in wide.columns):
                tmp = pd.to_numeric(wide["당기순이익"], errors="coerce").dropna()
                ni_last = _to_num(tmp.iloc[0]) if not tmp.empty else None
            if ni_last is None:
                _, nis = pick_by_alias(wide, "NI")
                if nis is not None:
                    s = pd.to_numeric(nis, errors="coerce").dropna()
                    ni_last = _to_num(s.iloc[0]) if not s.empty else None

            # Equity
            if ("자본총계" in wide.columns):
                tmp = pd.to_numeric(wide["자본총계"], errors="coerce").dropna()
                eq_last = _to_num(tmp.iloc[0]) if not tmp.empty else None
            if eq_last is None:
                _, eqs = pick_by_alias(wide, "EQUITY")
                if eqs is not None:
                    s = pd.to_numeric(eqs, errors="coerce").dropna()
                    eq_last = _to_num(s.iloc[0]) if not s.empty else None
    except Exception:
        pass

    # ---- 유효 계산값(최종) 초기값: KRX 값
    per = per_krx
    pbr = pbr_krx
    eps = eps_krx
    bps = bps_krx

    # ---- 수동 주식수 입력 시: EPS/BPS/PER/PBR을 수동 주식수 기준으로 재계산(가능한 범위)
    if manual_override:
        if (ni_last is not None) and (shares_eff not in (None, 0)) and np.isfinite(shares_eff) and float(shares_eff) != 0:
            try:
                eps = float(ni_last) / float(shares_eff)
            except Exception:
                eps = None

        if (eq_last is not None) and (shares_eff not in (None, 0)) and np.isfinite(shares_eff) and float(shares_eff) != 0:
            try:
                bps = float(eq_last) / float(shares_eff)
            except Exception:
                bps = None

        if (close is not None) and (eps not in (None, 0)) and np.isfinite(close) and np.isfinite(eps) and float(eps) != 0:
            try:
                per = float(close) / float(eps)
            except Exception:
                per = None
        else:
            per = None

        if (close is not None) and (bps not in (None, 0)) and np.isfinite(close) and np.isfinite(bps) and float(bps) != 0:
            try:
                pbr = float(close) / float(bps)
            except Exception:
                pbr = None
        else:
            pbr = None

    else:
        if (eps is None) and (ni_last is not None) and (shares_eff not in (None, 0)) and np.isfinite(shares_eff) and float(shares_eff) != 0:
            try:
                eps = float(ni_last) / float(shares_eff)
            except Exception:
                eps = None

        if (bps is None) and (eq_last is not None) and (shares_eff not in (None, 0)) and np.isfinite(shares_eff) and float(shares_eff) != 0:
            try:
                bps = float(eq_last) / float(shares_eff)
            except Exception:
                bps = None

        if (per is None) and (close is not None) and (eps not in (None, 0)) and np.isfinite(close) and np.isfinite(eps) and float(eps) != 0:
            try:
                per = float(close) / float(eps)
            except Exception:
                per = None

        if (pbr is None) and (close is not None) and (bps not in (None, 0)) and np.isfinite(close) and np.isfinite(bps) and float(bps) != 0:
            try:
                pbr = float(close) / float(bps)
            except Exception:
                pbr = None

    # -------------------------
    # 세션 반영
    # -------------------------
    if shares_eff is not None and np.isfinite(shares_eff) and float(shares_eff) > 0:
        st.session_state.shares = float(shares_eff)
    if mktcap_eff is not None and np.isfinite(mktcap_eff):
        st.session_state.mktcap = float(mktcap_eff)

    st.session_state.close = close
    st.session_state.mkt_date = asof
    st.session_state.fund = {
        "date": f_asof,
        "PER": per,
        "PBR": pbr,
        "EPS": eps,
        "BPS": bps,
        "DIV": _to_num(fund.get("DIV")),
    }

   

    # -------------------------
    # EV/EBITDA: 비어있으면 즉시 재계산(표/카드 표시 보장)
    # -------------------------
    evhist_local = evhist
    if evhist_local is None or evhist_local.empty:
        crtfc_key = st.session_state.get("sb_api_key", "") or ""
        corp_code = st.session_state.get("selected_corp_code", "") or ""
        end_year = int(st.session_state.get("sb_end_year", _now_kst().year - 1))
        n_years = int(st.session_state.get("sb_n_years", 5))
        reprt_code = st.session_state.get("reprt_code", "11011")
        fs_div = st.session_state.get("fs_div", "CFS")

        if crtfc_key and corp_code and sc:
            try:
                with st.spinner("EV/EBITDA(연도별) 직접계산 재시도 중..."):
                    evh2 = ev_ebitda_history(crtfc_key, corp_code, _ticker6(sc), end_year, n_years, reprt_code, fs_div, shares_eff)
                st.session_state.evhist = evh2
                evhist_local = evh2
            except Exception as _:
                evhist_local = pd.DataFrame()

    # -------------------------
    # KPI (6 cards: 3x2)
    # -------------------------
    r1c1, r1c2, r1c3 = st.columns(3)
    kpi(r1c1, "현재 주가(근사)", "-" if close is None else f"{float(close):,.0f}")
    kpi(r1c2, "시가총액", "-" if mktcap_eff is None else f"{float(mktcap_eff)/1e12:,.2f} 조원", sub=f"기준일: {asof or '-'}")
    kpi(r1c3, "발행주식수", "-" if shares_eff is None else f"{float(shares_eff)/1e6:,.0f} 백만주")

    r2c1, r2c2, r2c3 = st.columns(3)
    kpi(
        r2c1,
        "PER / PBR",
        "-" if (per is None or pbr is None) else f"{float(per):,.1f}x / {float(pbr):,.1f}x",
        sub=f"기준일: {f_asof or '-'}"
    )
    kpi(r2c2, "EPS", "-" if eps is None else f"{float(eps):,.0f}")
    kpi(r2c3, "BPS", "-" if bps is None else f"{float(bps):,.0f}")

    if st.session_state.market_msg:
        st.caption(st.session_state.market_msg)


    
    # =========================================================
    # ✅ (교체) 업종 밴드 기반 멀티플 평가 (KRX 업종평균 조회 없이)
    # - 업종 태그(좌측 선택) → 밴드 프리셋을 기본 선택
    # - (추가) 피어 기반 밴드 자동 산출(25/50/75) 기능
    # =========================================================
    industry_tag = st.session_state.industry_tag if "industry_tag" in st.session_state else "자동/미지정"
    st.markdown("### 🏷️ 업종 밴드 기반 멀티플 평가 (KRX 업종평균 조회 없이)")

    INDUSTRY_BAND_PRESETS = {
        "반도체/IT HW": {"PER": (10.0, 18.0, 26.0), "PBR": (1.2, 2.5, 4.0), "EV/EBITDA": (6.0, 10.0, 14.0),
            "note": "메모리/파운드리 업황과 증설 사이클 영향. PER은 저점·고점 편차가 커서 ‘정상화 이익’ 기준 해석 권장."},
        "화학/정유": {"PER": (5.0, 8.0, 12.0), "PBR": (0.4, 0.8, 1.3), "EV/EBITDA": (3.0, 5.5, 8.0),
            "note": "스프레드·가동률·원가(납사/에탄) 영향. 사이클 국면에 따라 밴드 이동폭 큼."},
        "조선": {"PER": (6.0, 10.0, 15.0), "PBR": (0.7, 1.3, 2.2), "EV/EBITDA": (4.0, 7.0, 10.0),
            "note": "수주잔고·선가·환율·원가(강재) 영향. 실적 인식 지연으로 ‘선행 지표’(수주/선가) 병행."},
        "해운": {"PER": (3.0, 6.0, 10.0), "PBR": (0.3, 0.9, 1.8), "EV/EBITDA": (2.0, 4.5, 7.0),
            "note": "운임·선복·유가 민감. 정상화 수준(중앙값)과 스팟 피크를 분리해 해석."},
        "철강": {"PER": (4.0, 7.0, 11.0), "PBR": (0.3, 0.7, 1.2), "EV/EBITDA": (3.0, 5.5, 8.0),
            "note": "스프레드·중국 수급·원재료 영향. 업황에 따라 밴드 저점이 낮아질 수 있음."},
        "제약/바이오": {"PER": (15.0, 25.0, 40.0), "PBR": (2.0, 3.8, 6.0), "EV/EBITDA": (10.0, 15.0, 22.0),
            "note": "임상/파이프라인 이벤트로 옵션 가치 포함. 적자 기업은 PER/EV/EBITDA 왜곡 가능."},
        "방산": {"PER": (10.0, 15.0, 22.0), "PBR": (1.2, 2.2, 3.5), "EV/EBITDA": (6.0, 9.0, 13.0),
            "note": "수주·수출 믹스·마진 레버리지. 지정학 프리미엄으로 상단 확장 가능."},
        "항공": {"PER": (5.0, 9.0, 14.0), "PBR": (0.5, 1.0, 1.8), "EV/EBITDA": (4.0, 6.5, 9.0),
            "note": "수요·유가·환율·리스 영향. EV/EBITDA 해석 시 순차입금(리스 포함 여부) 일관성 중요."},
        "유통": {"PER": (8.0, 12.0, 18.0), "PBR": (0.6, 1.2, 2.0), "EV/EBITDA": (5.0, 8.0, 12.0),
            "note": "성장률(동일점/온라인)·마진(판관비) 핵심. 자산가치가 PBR 하단을 지지."},
        "통신/유틸리티": {"PER": (7.0, 10.0, 14.0), "PBR": (0.6, 1.0, 1.6), "EV/EBITDA": (3.5, 5.5, 7.5),
            "note": "배당/현금흐름 가시성. 규제/요금/Capex 사이클 점검."},
        "은행": {"PER": (3.0, 5.0, 8.0), "PBR": (0.25, 0.55, 0.95), "EV/EBITDA": (None, None, None),
            "note": "금융주는 EV/EBITDA보다 PBR–ROE(또는 P/E–COE) 프레임이 정석."},
        "자동차": {"PER": (5.0, 8.0, 12.0), "PBR": (0.5, 0.9, 1.5), "EV/EBITDA": (3.0, 5.0, 7.5),
            "note": "판매믹스/환율/원가/인센티브 영향. 모빌리티·EV 전환, CAPEX/리스(금융) 구조까지 함께 점검."},
        "기타/일반": {"PER": (8.0, 12.0, 18.0), "PBR": (0.6, 1.2, 2.0), "EV/EBITDA": (4.0, 7.0, 11.0),
            "note": "업종 특성이 혼재. 밴드는 가이드로만 쓰고 정상화/리스크를 함께 점검."},
    }

    tag_to_band = {
        "반도체": "반도체/IT HW",
        "정유/화학": "화학/정유",
        "조선": "조선",
        "해운": "해운",
        "철강/소재": "철강",
        "제약바이오": "제약/바이오",
        "제약/바이오": "제약/바이오",
        "방산": "방산",
        "항공": "항공",
        "유통/소비": "유통",
        "유통": "유통",
        "은행": "은행",
        "보험": "은행",
        "통신": "통신/유틸리티",
        "자동차": "자동차",
    }

    # 현재 기업 멀티플(있으면)
    per_val = _to_num(per) if "per" in locals() else _to_num(st.session_state.get("per", None))
    pbr_val = _to_num(pbr) if "pbr" in locals() else _to_num(st.session_state.get("pbr", None))

    # EV/EBITDA: (있으면) 표에서 최신값 사용
    ev_ebitda_val = None
    if "evhist_local" in locals() and evhist_local is not None and not evhist_local.empty:
        df = evhist_local.copy()
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.sort_values("Date", ascending=False)
        row = df.iloc[0]
        ev_ebitda_val = _to_num(row.get("EV/EBITDA"))

    def _fmt_band(low, mid, high, unit="x"):
        if low is None or mid is None or high is None:
            return "N/A"
        return f"{low:.1f}{unit} ~ {high:.1f}{unit} (중심 {mid:.1f}{unit})"

    def _band_bucket(v, low, high):
        if v is None or low is None or high is None:
            return None
        v = float(v)
        if v < float(low):
            return "하단(디스카운트)"
        if v > float(high):
            return "상단(프리미엄)"
        return "밴드 내(정상 범위)"

    def _badge_from_bucket(metric, bucket):
        if bucket is None:
            return None
        if "프리미엄" in bucket:
            return (f"{metric} 프리미엄", "warn")
        if "디스카운트" in bucket:
            return (f"{metric} 디스카운트", "info")
        return (f"{metric} 밴드내", "ok")

    
    
    
    default_key = tag_to_band.get(industry_tag, "기타/일반")
    keys = list(INDUSTRY_BAND_PRESETS.keys())
    default_index = keys.index(default_key) if default_key in keys else 0

    industry_key = st.selectbox("업종 밴드 선택", keys, index=default_index)

    def _band_row(metric: str):
        return INDUSTRY_BAND_PRESETS[industry_key][metric]

    band_df = pd.DataFrame([
        {"Metric": "PER", "Low": _band_row("PER")[0], "Mid": _band_row("PER")[1], "High": _band_row("PER")[2]},
        {"Metric": "PBR", "Low": _band_row("PBR")[0], "Mid": _band_row("PBR")[1], "High": _band_row("PBR")[2]},
        {"Metric": "EV/EBITDA", "Low": _band_row("EV/EBITDA")[0], "Mid": _band_row("EV/EBITDA")[1], "High": _band_row("EV/EBITDA")[2]},
    ])

    edited = st.data_editor(band_df, use_container_width=True, hide_index=True, num_rows="fixed")

    # ✅ 업종 밴드 코멘트(롤백)
    per_low, per_mid, per_high = _band_row("PER")
    pbr_low, pbr_mid, pbr_high = _band_row("PBR")
    ev_low, ev_mid, ev_high = _band_row("EV/EBITDA")

    bullets = [
        f"선택 업종 밴드: <b>{industry_key}</b> (업종 태그: {industry_tag})",
        f"PER 밴드: {_fmt_band(per_low, per_mid, per_high, unit='x')}",
        f"PBR 밴드: {_fmt_band(pbr_low, pbr_mid, pbr_high, unit='x')}",
        f"EV/EBITDA 밴드: {_fmt_band(ev_low, ev_mid, ev_high, unit='x')}",
    ]

    badges = []
    b1 = _badge_from_bucket("PER", _band_bucket(per_val, per_low, per_high))
    b2 = _badge_from_bucket("PBR", _band_bucket(pbr_val, pbr_low, pbr_high))
    b3 = _badge_from_bucket("EV/EBITDA", _band_bucket(ev_ebitda_val, ev_low, ev_high))
    for b in (b1, b2, b3):
        if b:
            badges.append(b)

    def _fmt_now(v, unit="x"):
        return "N/A" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{float(v):.1f}{unit}"

    bullets.append(f"현재(최근) 지표: PER {_fmt_now(per_val)} / PBR {_fmt_now(pbr_val)} / EV/EBITDA {_fmt_now(ev_ebitda_val)}")

    note = INDUSTRY_BAND_PRESETS[industry_key].get("note", "")
    if note:
        bullets.append(f"업종 메모: {note}")

    render_commentary_box("업종 밴드 코멘트", bullets, badges)


   
    
    # -------------------------
    # Price chart
    # -------------------------
    st.markdown('<div class="section-title">📉 주가(최근 1년) 추이</div>', unsafe_allow_html=True)
    ch = alt_time_series(price_df, "Date", "Close", "Close", fmt=",.0f", color=COLOR["price"])
    render_plain_chart(f"{info.get('stock_code','')} Close", ch)

    
    # -------------------------
    # 총차입금 / 현금 / 감가상각비 / CAPEX (연도별) + EV/EBITDA 보조표
    # -------------------------
    st.markdown('<div class="section-title">🏦 총차입금 · 현금 · 감가상각비 · CAPEX (연도별)</div>', unsafe_allow_html=True)

    crtfc_key = st.session_state.get("sb_api_key", "") or ""
    corp_code = st.session_state.get("selected_corp_code", "") or ""
    end_year = int(st.session_state.get("sb_end_year", _now_kst().year - 1))
    n_years = int(st.session_state.get("sb_n_years", 5))
    reprt_code = st.session_state.get("reprt_code", "11011")
    fs_div = st.session_state.get("fs_div", "CFS")

        # 총차입금 산정 모드 (EV 시총 기준 선택 제거 → 시총 연도별 수동 입력)
    debt_mode_label = st.radio(
        "총차입금 산정",
        ["차입금+사채(리스 제외)", "이자발생부채(리스 포함)"],
        horizontal=True,
        key="debt_mode_label",
    )
    debt_mode = "core" if debt_mode_label.startswith("차입금") else "ib"

    dc = None
    if crtfc_key and corp_code:
        try:
            dc = debt_cash_da_capex_history(
                crtfc_key, corp_code, end_year, n_years, reprt_code, fs_div, debt_mode=debt_mode
            )
        except Exception:
            dc = None

    if dc is None or dc.empty:
        st.info("표를 만들 데이터가 없습니다(계정 결측/조회 실패 가능).")
        return

    def _to_tril(x):
        try:
            if x is None:
                return np.nan
            v = float(x)
            if not np.isfinite(v):
                return np.nan
            return v / 1e12
        except Exception:
            return np.nan

    show = dc.copy()
    show["Year"] = show["Year"].astype(int).astype(str)

    capex_col = "CAPEX(유무형)"
    if "CAPEX" in show.columns and capex_col not in show.columns:
        show = show.rename(columns={"CAPEX": capex_col})

    show["총차입금_tr"] = show["총차입금"].map(_to_tril)
    show["현금_tr"] = show["현금 및 현금성 자산"].map(_to_tril)
    show["영업이익_tr"] = show["영업이익"].map(_to_tril)
    show["capex_tr"] = show[capex_col].map(_to_tril)

    # 감가상각비(유무형): 수동 입력
    dep_map = st.session_state.setdefault("manual_dep_map", {})
    corp_dep = dep_map.get(corp_code, {})

    dep_init = []
    for _, r in show.iterrows():
        y = str(r.get("Year", ""))
        v = corp_dep.get(y, None)
        if v is None:
            auto_da = r.get("감가상각비(유무형)", np.nan)
            v = _to_tril(auto_da) if auto_da is not None else np.nan
        dep_init.append(v)

    show["감가상각비(유무형)_tr_manual"] = dep_init

    left_df = pd.DataFrame({
        "Year": show["Year"],
        "총차입금": show["총차입금_tr"],
        "현금 및 현금성 자산": show["현금_tr"],
        "감가상각비(유무형)": show["감가상각비(유무형)_tr_manual"],
        capex_col: show["capex_tr"],
    })

        # ✅ 3개 표를 한 줄에 (좌/중/우)로 배치해서 EV/EBITDA 안 잘리게
    # 좌: 총차입금/현금/감가/CAPEX
    # 중: EV/EBITDA
    # 우: 시총(조원) 수동 입력
    left_col, ev_col, mcap_col = st.columns([1.65, 1.15, 0.70], vertical_alignment="top")
    _tbl_h = 320

    # ✅ 편집 가능한 입력칸(감가/시총) 동일 색상 처리 (data_editor의 input만 색칠)
    st.markdown(
        """
        <style>
        /* 편집 가능한 입력칸(input) 색 */
        div[data-testid="stDataFrame"] div[role="gridcell"] input {
            background-color: #fff6cc !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
        }

        /* ✅ data_editor / dataframe 헤더 전체 굵게 */
        div[data-testid="stDataFrame"] thead th,
        div[data-testid="stDataFrame"] [role="columnheader"] {
            font-weight: 900 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


    with left_col:
        st.caption("★★★ 감가상각비(유무형)은 수동 입력(조원)입니다. 입력 즉시 우측 EV/EBITDA가 재계산됩니다.")
        edited = st.data_editor(
            left_df,
            hide_index=True,
            use_container_width=True,
            height=_tbl_h,
            key=f"dep_editor_{corp_code}_{end_year}_{n_years}",
            disabled=["Year", "총차입금", "현금 및 현금성 자산", capex_col],
            column_config={
                "Year": st.column_config.TextColumn("Year"),
                "총차입금": st.column_config.NumberColumn("총차입금", format="%.3f"),
                "현금 및 현금성 자산": st.column_config.NumberColumn("현금 및 현금성 자산", format="%.3f"),
                "감가상각비(유무형)": st.column_config.NumberColumn("감가상각비(유무형)", format="%.3f"),
                capex_col: st.column_config.NumberColumn(capex_col, format="%.3f"),
            },
        )

        new_corp_dep = {}
        for _, r in edited.iterrows():
            y = str(r.get("Year", "")).strip()
            v = r.get("감가상각비(유무형)", np.nan)
            try:
                v = float(v)
                if not np.isfinite(v):
                    v = None
            except Exception:
                v = None
            if y:
                new_corp_dep[y] = v
        dep_map[corp_code] = new_corp_dep
        st.session_state["manual_dep_map"] = dep_map

    # ✅ 시총(조원) 연도별 수동 입력표 (우측)
    mktcap_tr_current = (float(mktcap_eff) / 1e12) if (mktcap_eff is not None and np.isfinite(float(mktcap_eff))) else np.nan
    mcap_map_all = st.session_state.setdefault("manual_mktcap_map", {})
    corp_mcap = mcap_map_all.get(corp_code, {})

    mcap_init = []
    for _, r in edited.iterrows():
        y = str(r.get("Year", "")).strip()
        v = corp_mcap.get(y, None)
        if v is None:
            v = mktcap_tr_current
        mcap_init.append(v)

    mcap_df = pd.DataFrame({
        "Year": edited["Year"].astype(str),
        "시총(조원)": mcap_init,
    })

    with mcap_col:
        st.caption("★★★ 시총(조원)은 수동 입력입니다.")
        mcap_edited = st.data_editor(
            mcap_df,
            hide_index=True,
            use_container_width=True,
            height=_tbl_h,
            key=f"mcap_editor_{corp_code}_{end_year}_{n_years}",
            disabled=["Year"],
            column_config={
                "Year": st.column_config.TextColumn("Year"),
                "시총(조원)": st.column_config.NumberColumn("시총(조원)", format="%.3f"),
            },
        )

        new_corp_mcap = {}
        for _, rr in mcap_edited.iterrows():
            yy = str(rr.get("Year", "")).strip()
            vv = rr.get("시총(조원)", np.nan)
            try:
                vv = float(vv)
                if not np.isfinite(vv):
                    vv = None
            except Exception:
                vv = None
            if yy:
                new_corp_mcap[yy] = vv

        mcap_map_all[corp_code] = new_corp_mcap
        st.session_state["manual_mktcap_map"] = mcap_map_all

    mktcap_tr_map = {str(k): v for k, v in mcap_map_all.get(corp_code, {}).items()}

    # ✅ EV/EBITDA 계산(시총=수동 입력)
    ev_list, ebitda_list, mult_list = [], [], []

    for _, r in edited.iterrows():
        y = str(r.get("Year", "")).strip()

        debt_tr = r.get("총차입금", np.nan)
        cash_tr = r.get("현금 및 현금성 자산", np.nan)
        dep_tr = r.get("감가상각비(유무형)", np.nan)

        hit = show[show["Year"] == y]
        op_tr = float(hit.iloc[0]["영업이익_tr"]) if (not hit.empty) else np.nan

        mktcap_tr = mktcap_tr_map.get(y, np.nan)

        ev_tr = (float(mktcap_tr) + float(debt_tr) - float(cash_tr)) if np.isfinite(mktcap_tr) and np.isfinite(debt_tr) and np.isfinite(cash_tr) else np.nan
        ebitda_tr = (float(op_tr) + float(dep_tr)) if np.isfinite(op_tr) and np.isfinite(dep_tr) else np.nan
        mult = (ev_tr / ebitda_tr) if (np.isfinite(ev_tr) and np.isfinite(ebitda_tr) and ebitda_tr != 0) else np.nan

        ev_list.append(ev_tr)
        ebitda_list.append(ebitda_tr)
        mult_list.append(mult)

    right_df = pd.DataFrame({
        "Year": edited["Year"].astype(str),
        "EV(조원)": ev_list,
        "EBITDA(조원)": ebitda_list,
        "EV/EBITDA": mult_list,   # ✅ 컬럼명을 짧게 해서 잘림 방지
    })

    sty = (
        right_df.style
        .set_table_styles([{"selector": "th", "props": [("font-weight", "900")]}])
        .set_properties(subset=["Year"], **{"text-align": "left"})
        .set_properties(subset=["EV(조원)"], **{"background-color": "#fff7ed", "font-weight": "700"})
        .set_properties(subset=["EBITDA(조원)"], **{"background-color": "#ecfdf5", "font-weight": "700"})
        .set_properties(subset=["EV/EBITDA"], **{"background-color": "#eef2ff", "font-weight": "800"})
        .format({"EV(조원)": "{:.3f}", "EBITDA(조원)": "{:.3f}", "EV/EBITDA": "{:.2f}"})
    )

    with ev_col:
        st.caption("※ EV/EBITDA는 시총·감가 입력에 따라 자동 재계산됩니다.")
        st.dataframe(sty, use_container_width=True, height=_tbl_h)




def render_peer_bridge(crtfc_key: str, info: dict, end_year: int, n_years: int, reprt_code: str, fs_div: str):
    """
    Peer 탭(전면 교체):
    - 사용자가 입력한 Peer 종목코드들에 대해
      1) 기업별 5개 핵심지표 그래프(총 5*N개)를 먼저 출력
      2) 그 아래에 기업별 BS 히스토리 표(N개)를 순서대로 출력
    """
    unit = st.session_state.get("unit", "원")

    st.markdown('<div class="section-title">🏷️ Peer</div>', unsafe_allow_html=True)

    # 기존 "Peer에서 제공하는 값" 안내 박스 교체
    st.info(
        "Peer 탭 출력 내용\n"
        "• 입력한 Peer 종목별 ‘핵심 지표 추이’ 5개 그래프를 먼저 모아서 출력합니다.\n"
        "• 그 아래에 입력한 Peer 종목별 ‘BS 히스토리’ 표를 기업별로 순서대로 출력합니다.\n"
        "• Peer 선정(동종업계/규모/시총 유사)은 사용자가 입력한 종목코드 기준입니다."
    )

    st.markdown("### 1) Peer 종목코드 입력")
    peer_text = st.text_area(
        "예: 005930 000660 051910 (쉼표/공백/줄바꿈 모두 가능)",
        value=st.session_state.get("peer_codes_text", ""),
        height=80,
        key="peer_codes_text",
    )

    run = st.button("Peer 그래프/BS 출력", use_container_width=True)

    if not run:
        return

    # ---- 입력 파싱
    raw = (peer_text or "").replace(",", " ").replace("\t", " ")
    codes = [c.strip() for c in raw.split() if c.strip()]
    codes = ["".join([x for x in c if x.isdigit()]).zfill(6) for c in codes]
    # 중복 제거(입력 순서 유지)
    seen = set()
    peer_codes = []
    for c in codes:
        if c and c not in seen:
            peer_codes.append(c)
            seen.add(c)

    if not peer_codes:
        st.warning("Peer 종목코드를 입력하세요.")
        return

    # ---- corp master 로드 (DART)
    try:
        master = load_corp_master(crtfc_key)
    except Exception as e:
        st.error(f"DART corp master 로드 실패: {e}")
        return

    # ---- Peer별 데이터 준비
    peer_items = []
    for t6 in peer_codes:
        hit = find_corp_code(master, "종목코드", t6)
        if hit is None or hit.empty:
            st.warning(f"종목코드 {t6}: DART corp_code 매칭 실패(상장/매칭 누락 가능).")
            continue

        corp_code = str(hit.iloc[0]["corp_code"]).strip()
        corp_name = str(hit.iloc[0]["corp_name"]).strip()

        # IS wide(그래프용)
        wide_is, y2t_is = fetch_last_n_years_is_wide(crtfc_key, corp_code, end_year, n_years, reprt_code, fs_div)

        # BS wide(표용)
        wide_bs, y2t_bs = fetch_last_n_years_wide(crtfc_key, corp_code, end_year, n_years, reprt_code, fs_div)

        peer_items.append({
            "ticker6": t6,
            "corp_code": corp_code,
            "corp_name": corp_name,
            "wide_is": wide_is,
            "y2t_is": y2t_is,
            "wide_bs": wide_bs,
            "y2t_bs": y2t_bs,
        })

    if not peer_items:
        st.warning("출력 가능한 Peer 데이터가 없습니다.")
        return

    # =========================================================
    # 1) 그래프 먼저: 기업별 5개씩 -> 총 5*N개
    # =========================================================
    st.markdown('<div class="section-title">📈 Peer 핵심 지표 추이</div>', unsafe_allow_html=True)
    st.caption("기업별로 5개 그래프(매출/원가율/영업이익/영업이익률/순이익)가 순서대로 출력됩니다.")

    for it in peer_items:
        st.markdown(f"#### {it['corp_name']} ({it['ticker6']})")
        render_core_charts_peer(it["wide_is"], unit, title=None)

    # =========================================================
    # 2) 그 아래 BS 표: 기업별 1개씩 -> 총 N개
    # =========================================================
    st.write("")
    st.markdown('<div class="section-title">📦 Peer BS 히스토리</div>', unsafe_allow_html=True)
    st.caption("기업별 BS 히스토리 표가 순서대로 출력됩니다.")

    for it in peer_items:
        st.markdown(f"#### {it['corp_name']} ({it['ticker6']})")
        render_bs_history_only(it["wide_bs"], it["y2t_bs"], unit, title=None)




def render_dcf_wacc(info: dict, wide: pd.DataFrame, unit: str, industry_tag: str):
    st.markdown('<div class="section-title">🧮 WACC → DCF (FCFF)</div>', unsafe_allow_html=True)

    _, rev_s = pick_by_alias(wide, "REV")
    _, op_s  = pick_by_alias(wide, "OP")

    base_year = int(wide.index.max()) if wide is not None and not wide.empty else None
    base_revenue = last_value(rev_s)
    base_op = last_value(op_s)

    if base_year is None or base_revenue is None:
        st.warning("DCF를 계산하려면 최소한 '매출(또는 수익)'이 필요합니다.")
        return

    ratios, base = compute_fin_ratios(wide)
    opm_hist = None
    if base["rev"] is not None and base["op"] is not None:
        opm_hist = (base["op"] / base["rev"]).replace([np.inf, -np.inf], np.nan)

    rev_hist = pd.to_numeric(base["rev"], errors="coerce") if base["rev"] is not None else None
    rev_cagr_suggest = 0.05
    if rev_hist is not None:
        s = rev_hist.dropna()
        if len(s) >= 3:
            ss = s.sort_index()
            y0 = float(ss.iloc[-3])
            y2 = float(ss.iloc[-1])
            if y0 > 0 and y2 > 0:
                rev_cagr_suggest = (y2 / y0) ** (1/2) - 1

    opm_suggest = float(np.nanmedian(opm_hist.dropna())) if (opm_hist is not None and not opm_hist.dropna().empty) else 0.06

    nwc_pct_default = 0.05
    try:
        nwc_series = ratios.get("NWC")
        rev_series = base.get("rev")
        if nwc_series is not None and rev_series is not None:
            nwc_last = last_value(nwc_series)
            rev_last = last_value(rev_series)
            if (nwc_last is not None) and (rev_last not in (None, 0)):
                nwc_pct_default = float(nwc_last / rev_last)
    except Exception:
        pass

    st.markdown(
        "<div class='card-soft'><b style='color:#0f172a;'>WACC 원리</b><br/>"
        "<span style='color:rgba(15,23,42,0.70);'>"
        "Ke = rf + β×MRP (CAPM)<br/>"
        "WACC = E/(D+E)×Ke + D/(D+E)×Kd×(1-세율)<br/>"
        "β는 KRX 일간수익률 회귀로 산출(결측 가능). rf/MRP는 기관/가정에 따라 달라 수동 조정 구조 유지."
        "</span></div>",
        unsafe_allow_html=True
    )

    auto_beta = st.session_state.beta_val if st.session_state.beta_ok else None
    dte_last = last_value(ratios.get("D/E")) if ratios.get("D/E") is not None else None
    if dte_last is None:    
        dte_last = 0.3

    rf = st.number_input("무위험이자율(rf) ■ 5년만기 국공채수익률 이용", value=0.035, step=0.0025, format="%.4f", key="wacc_rf")
    mrp = st.number_input("시장위험프리미엄(MRP)  ■ 한공회(한국공인회계사회) 수치 이용", value=0.055, step=0.0025, format="%.4f", key="wacc_mrp")
    beta = st.number_input("Beta(β)", value=float(auto_beta) if auto_beta is not None else 1.0, step=0.05, format="%.4f", key="wacc_beta")
    kd = st.number_input("부채비용(Kd)", value=0.05, step=0.0025, format="%.4f", key="wacc_kd")
    tax_rate = st.number_input("법인세율 ■ 2억이하 10% , 2억~200억 : 20% , 200억 ~ 3000억 : 22% , 3000억 ~ : 25%", value=0.24, step=0.01, format="%.4f", key="wacc_tax")
    dte = st.number_input("D/E ■ 부채/자기자본 ", value=float(dte_last) if dte_last is not None else 0.3, step=0.05, format="%.4f", key="wacc_dte")

    ke = float(rf + beta * mrp)
    wD = float(dte / (1 + dte))
    wE = float(1 / (1 + dte))
    wacc = float(wE * ke + wD * kd * (1 - tax_rate))

    kA, kB, kC = st.columns(3)
    kpi(kA, "Ke (CAPM)", f"{ke*100:.2f} %")
    kpi(kB, "WACC", f"{wacc*100:.2f} %")
    kpi(kC, "세후 Kd", f"{(kd*(1-tax_rate))*100:.2f} %")

    st.markdown('<div class="section-title">📌 DCF 입력 (과거 기반 추천값 포함)</div>', unsafe_allow_html=True)

    # ✅ 요청: 표 재구성(매출, 매출성장률, 영업이익률, 감가/매출, capex/매출, nwc/매출 전부)
    hist = pd.DataFrame(index=wide.index.sort_values(ascending=True))
    if rev_hist is not None:
        hist["매출"] = rev_hist.sort_index()
        hist["매출성장률"] = hist["매출"].pct_change()
    if opm_hist is not None:
        hist["영업이익률"] = opm_hist.sort_index()

    # ✅ 감가/매출, CAPEX/매출: DART에서 뽑은 "실제 값"으로 계산
    #   - 감가상각비는 "시장/멀티플"에서 사용자가 입력한 수동값(manual_dep_map)이 있으면 그 값이 우선 적용됩니다.
    corp_code = str(info.get("corp_code") or st.session_state.get("selected_corp_code") or "").strip()
    end_year = int(st.session_state.get("sb_end_year", base_year))
    n_years = int(st.session_state.get("sb_n_years", 5))
    reprt_code = st.session_state.get("reprt_code", "11011")
    fs_div = st.session_state.get("fs_div", "CFS")
    debt_mode = st.session_state.get("debt_mode", "core")

    dc_hist = pd.DataFrame()
    if corp_code:
        try:
            dc_hist = debt_cash_da_capex_history(
                crtfc_key=crtfc_key,
                corp_code=corp_code,
                end_year=end_year,
                n_years=n_years,
                reprt_code=reprt_code,
                fs_div=fs_div,
                debt_mode=debt_mode,
            )
        except Exception:
            dc_hist = pd.DataFrame()

    da_pct_auto = None
    capex_pct_auto = None
    try:
        if (dc_hist is not None) and (not dc_hist.empty) and ("매출" in hist.columns):
            tmp = dc_hist.set_index("Year").sort_index()
            da_s = pd.to_numeric(tmp.get("감가상각비(유무형)"), errors="coerce")
            capex_s = pd.to_numeric(tmp.get("CAPEX"), errors="coerce")

            # (1) 감가상각비: 수동 입력값(조원) → 원으로 변환하여 override
            manual_map = (st.session_state.get("manual_dep_map") or {}).get(str(corp_code), {})
            if isinstance(manual_map, dict):
                for yy, v_tr in manual_map.items():
                    try:
                        y_int = int(str(yy).strip())
                        v_num = _to_num(v_tr)
                        if v_num is not None and np.isfinite(v_num):
                            da_s.loc[y_int] = float(v_num) * 1e12
                    except Exception:
                        pass

            rv = pd.to_numeric(hist["매출"], errors="coerce")
            hist["감가/매출"] = (da_s.reindex(rv.index) / rv).replace([np.inf, -np.inf], np.nan)
            hist["CAPEX/매출"] = (capex_s.reindex(rv.index) / rv).replace([np.inf, -np.inf], np.nan)

            # (2) DCF 입력 기본값(자동): 최근연도 비율(수동 감가 반영)
            if base_year in rv.index and (rv.loc[base_year] not in (None, 0)) and np.isfinite(rv.loc[base_year]):
                da_last = hist["감가/매출"].loc[base_year] if "감가/매출" in hist.columns else np.nan
                capex_last = hist["CAPEX/매출"].loc[base_year] if "CAPEX/매출" in hist.columns else np.nan
                da_pct_auto = float(da_last) if pd.notna(da_last) else None
                capex_pct_auto = float(capex_last) if pd.notna(capex_last) else None
    except Exception:
        pass

    if ratios.get("NWC") is not None and base.get("rev") is not None:
        nwc = pd.to_numeric(ratios["NWC"], errors="coerce").sort_index()
        rv2 = pd.to_numeric(base["rev"], errors="coerce").sort_index()
        hist["NWC/매출"] = (nwc / rv2).replace([np.inf, -np.inf], np.nan)

    if not hist.empty:
        disp = hist.copy()
        if "매출" in disp.columns:
            disp["매출"] = disp["매출"].map(
                lambda v: "" if pd.isna(v) else (f"{float(v)/1e12:,.3f} 조원" if is_trillion_mode(unit) else f"{float(v):,.0f}")
            )
        if "매출성장률" in disp.columns:
            disp["매출성장률"] = disp["매출성장률"].map(lambda v: "" if pd.isna(v) else f"{float(v)*100:,.1f}%")
        if "영업이익률" in disp.columns:
            disp["영업이익률"] = disp["영업이익률"].map(lambda v: "" if pd.isna(v) else f"{float(v)*100:,.1f}%")
        if "감가/매출" in disp.columns:
            disp["감가/매출"] = disp["감가/매출"].map(lambda v: "" if pd.isna(v) else f"{float(v)*100:,.1f}%")
        if "CAPEX/매출" in disp.columns:
            disp["CAPEX/매출"] = disp["CAPEX/매출"].map(lambda v: "" if pd.isna(v) else f"{float(v)*100:,.1f}%")
        if "NWC/매출" in disp.columns:
            disp["NWC/매출"] = disp["NWC/매출"].map(lambda v: "" if pd.isna(v) else f"{float(v)*100:,.1f}%")
        st.dataframe(disp, use_container_width=True, height=260)

    st.markdown(
        "<div style='margin:6px 0 2px 0;'>"
        + badge_html(f"매출 CAGR 추천: {rev_cagr_suggest*100:.1f}%", "info")
        + badge_html(f"OPM(중앙값) 추천: {opm_suggest*100:.1f}%", "info")
        + badge_html(f"NWC/매출(최근) 추천: {nwc_pct_default*100:.1f}%", "info")
        + (badge_html(f"감가/매출(최근, 연동): {da_pct_auto*100:.1f}%", "info") if da_pct_auto is not None else "")
        + (badge_html(f"CAPEX/매출(최근, 실제): {capex_pct_auto*100:.1f}%", "info") if capex_pct_auto is not None else "")
        + "</div>",
        unsafe_allow_html=True
    )

    default_margin = (base_op / base_revenue) if (base_op is not None and base_revenue) else opm_suggest
    default_margin = float(np.clip(default_margin, -0.5, 0.5))

    # ✅ 자동 연동: (시장/멀티플 수동 감가, DART CAPEX) → DCF 입력 기본값에 반영
    # - 사용자가 DCF 입력칸을 직접 바꾼 경우엔(=직전 자동값과 다름) 자동으로 덮어쓰지 않습니다.
    if da_pct_auto is None or not np.isfinite(da_pct_auto):
        da_pct_auto = 0.02
    if capex_pct_auto is None or not np.isfinite(capex_pct_auto):
        capex_pct_auto = 0.03

    prev_auto_da = st.session_state.get("_dcf_da_pct_auto_synced")
    cur_da = st.session_state.get("dcf_da_pct_sales")
    if (cur_da is None) or (prev_auto_da is None) or (abs(float(cur_da) - float(prev_auto_da)) < 1e-12):
        st.session_state["dcf_da_pct_sales"] = float(da_pct_auto)
    st.session_state["_dcf_da_pct_auto_synced"] = float(da_pct_auto)

    prev_auto_capex = st.session_state.get("_dcf_capex_pct_auto_synced")
    cur_capex = st.session_state.get("dcf_capex_pct_sales")
    if (cur_capex is None) or (prev_auto_capex is None) or (abs(float(cur_capex) - float(prev_auto_capex)) < 1e-12):
        st.session_state["dcf_capex_pct_sales"] = float(capex_pct_auto)
    st.session_state["_dcf_capex_pct_auto_synced"] = float(capex_pct_auto)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        horizon = st.number_input("예측 기간(년)", 3, 15, 5, 1, key="dcf_horizon")
        sales_cagr = st.number_input("매출 성장률(연)", value=float(rev_cagr_suggest), step=0.01, format="%.4f", key="dcf_sales_cagr")
        op_margin = st.number_input("영업이익률", value=float(default_margin), step=0.01, format="%.4f", key="dcf_op_margin")
    with c2:
        da_pct_sales = st.number_input(
            "감가상각/매출",
            value=float(st.session_state.get("dcf_da_pct_sales", 0.02)),
            step=0.005, format="%.4f", key="dcf_da_pct_sales"
        )
        capex_pct_sales = st.number_input(
            "CAPEX/매출",
            value=float(st.session_state.get("dcf_capex_pct_sales", 0.03)),
            step=0.005, format="%.4f", key="dcf_capex_pct_sales"
        )
    with c3:
        nwc_pct_sales = st.number_input("NWC/매출", value=float(nwc_pct_default), step=0.01, format="%.4f", key="dcf_nwc_pct_sales")
        terminal_g = st.number_input("Terminal g", value=0.02, step=0.005, format="%.4f", key="dcf_terminal_g")
    with c4:
        evh = st.session_state.evhist
        nd_auto = 0.0
        if evh is not None and not evh.empty and _to_num(evh.iloc[0].get("NetDebt")) is not None:
            nd_auto = float(evh.iloc[0].get("NetDebt"))
        net_debt = st.number_input("순차입금(Net Debt, 원)", value=float(nd_auto), step=1_000_000_000.0, format="%.0f", key="dcf_net_debt")
        shares_auto = st.session_state.shares if st.session_state.shares is not None else 1.0
        shares = st.number_input("발행주식수(주)", value=float(shares_auto), step=1.0, format="%.0f", key="dcf_shares")

    wacc_used = st.number_input("DCF 할인율(WACC 적용)", value=float(wacc), step=0.0025, format="%.4f", key="dcf_wacc_used")

    if float(wacc_used) <= float(terminal_g):
        st.error("WACC는 Terminal g 보다 커야 합니다. (WACC > g)")
        return
    if float(shares) <= 0:
        st.error("발행주식수는 0보다 커야 합니다.")
        return

    fcff_df = build_fcff_forecast(
        base_year=base_year,
        base_revenue=float(base_revenue),
        horizon=int(horizon),
        sales_cagr=float(sales_cagr),
        op_margin=float(op_margin),
        tax_rate=float(tax_rate),
        da_pct_sales=float(da_pct_sales),
        capex_pct_sales=float(capex_pct_sales),
        nwc_pct_sales=float(nwc_pct_sales),
    )

    out = dcf_valuation(
        fcff_df=fcff_df,
        wacc=float(wacc_used),
        terminal_g=float(terminal_g),
        net_debt=float(net_debt),
        shares_outstanding=float(shares),
    )

    st.markdown('<div class="section-title">📈 DCF 결과</div>', unsafe_allow_html=True)
    r1, r2, r3 = st.columns(3)
    kpi(r1, "Intrinsic Price(원)", f"{out['Price']:,.0f}")
    kpi(r2, "Enterprise Value(원)", f"{out['EV']:,.0f}")
    kpi(r3, "Equity Value(원)", f"{out['Equity']:,.0f}")

    st.markdown('<div class="section-title"> ■ PV 분해 </div>', unsafe_allow_html=True)
    r1, r2, r3 = st.columns(3)
    kpi(r1, "FCFF 현재가치", fmt_money_value(float(out["PV_FCFF"]), unit))
    kpi(r2, "TV(잔존가치) 현재가치", fmt_money_value(float(out["PV_TV"]), unit))
    kpi(r3, "TV(잔존가치) 비중", f"{out['TV_Share']*100:.1f}%" if np.isfinite(out["TV_Share"]) else "-")


    st.markdown('<div class="section-title">🧪 민감도(WACC × g)</div>', unsafe_allow_html=True)
    g_list = [float(terminal_g) - 0.01, float(terminal_g), float(terminal_g) + 0.01]
    w_list = [float(wacc_used) - 0.01, float(wacc_used), float(wacc_used) + 0.01]

    rows = []
    for w in w_list:
        row = {"WACC": w}
        for g in g_list:
            if w <= g:
                row[f"g={g:.2%}"] = np.nan
                continue
            tmp = dcf_valuation(fcff_df, float(w), float(g), float(net_debt), float(shares))
            row[f"g={g:.2%}"] = tmp["Price"]
        rows.append(row)
    sens = pd.DataFrame(rows).set_index("WACC")

    sens_disp = sens.copy()
    for c in sens_disp.columns:
        sens_disp[c] = sens_disp[c].map(lambda v: "" if (v is None or (isinstance(v, float) and np.isnan(v))) else f"{float(v):,.0f}")
    sens_disp.index = sens_disp.index.map(lambda v: f"{v:.2%}")
    sens_disp.index.name = "WACC"
    st.dataframe(sens_disp, use_container_width=True, height=df_height(sens_disp, max_rows=len(sens_disp)))



# =========================================================
# 15) Render main
# =========================================================
render_header()

with st.sidebar:
    if st.button("🔄 다른 회사로 전환(초기화)", use_container_width=True):
        reset_all()
        st.rerun()

    st.markdown("### 입력")
    crtfc_key = st.text_input("DART API 키", type="password", placeholder="붙여넣기", key="sb_api_key")

    mode = st.selectbox("검색 기준", ["회사명", "종목코드"], index=0)
    query = st.text_input("회사명/종목코드", placeholder="예: HD현대중공업 또는 329180")

    this_year = _now_kst().year
    colA, colB = st.columns(2)
    with colA:
        end_year = st.selectbox("기준연도", [y for y in range(this_year, 2014, -1)], index=1, key="sb_end_year")
    with colB:
        n_years = st.selectbox("기간(년)", [3, 5, 7, 10], index=1, key="sb_n_years")

    colC, colD = st.columns(2)
    with colC:
        reprt_map = {"사업(11011)": "11011", "반기(11012)": "11012", "1Q(11013)": "11013", "3Q(11014)": "11014"}
        reprt_label = st.selectbox("보고서", list(reprt_map.keys()), index=0, key="sb_reprt_label")
        reprt_code = reprt_map[reprt_label]
    with colD:
        fs_div_label = st.selectbox("연결/별도", ["연결(CFS)", "별도(OFS)"], index=0, key="sb_fs_div_label")
        fs_div = "CFS" if "CFS" in fs_div_label else "OFS"

    st.session_state.reprt_code = reprt_code
    st.session_state.fs_div = fs_div

    st.markdown("### 업종(선택)")
    st.session_state.industry_tag = st.selectbox(
        "업종 태그",
        INDUSTRY_TAGS,
        index=INDUSTRY_TAGS.index(st.session_state.industry_tag) if st.session_state.industry_tag in INDUSTRY_TAGS else 0,
        key="sb_industry"
    )

    st.write("")
    search_btn = st.button("① 회사 검색", use_container_width=True)
    fetch_btn = st.button("② 재무 가져오기", use_container_width=True)

    # =========================================================
    # ✅ (추가) 하단: 회사명 → 후보리스트(클릭) → 종목코드 + 피어표(20개)
    # =========================================================
    st.markdown("---")
    st.markdown("### 🔎 종목코드/피어 찾기(하단)")

    quick_query = st.text_input("회사명 입력", placeholder="예: 하이닉스", key="quick_query")

    # 선택 결과 저장 공간
    if "quick_corp_name" not in st.session_state:
        st.session_state.quick_corp_name = ""
    if "quick_stock_code" not in st.session_state:
        st.session_state.quick_stock_code = ""
    if "quick_corp_code" not in st.session_state:
        st.session_state.quick_corp_code = ""

    if quick_query.strip() and not crtfc_key:
        st.info("DART API 키를 입력하면 하단 검색 결과(후보 리스트)가 뜹니다.")

    master_q = None
    if crtfc_key:
        try:
            master_q = load_corp_master(crtfc_key)
        except Exception as e:
            master_q = None
            st.caption(f"DART 마스터 로드 오류: {e}")

    # 1) 회사명 검색 → 후보 리스트(클릭 선택)
    if master_q is not None and quick_query.strip():
        cand = find_corp_code(master_q, "회사명", quick_query).copy()

        if cand is None or cand.empty:
            st.caption("검색 결과가 없습니다.")
        else:
            cand["stock_code"] = cand["stock_code"].astype(str).str.strip()
            cand["stock_code_show"] = cand["stock_code"].where(cand["stock_code"].str.fullmatch(r"\d{6}", na=False), "-")
            cand = cand.sort_values(["corp_name", "stock_code_show"]).head(120)

            options = (cand["corp_name"] + " | " + cand["stock_code_show"] + " | " + cand["corp_code"]).tolist()
            picked = st.selectbox("검색 결과(클릭 선택)", ["— 선택 —"] + options, index=0, key="quick_pick2")

            if picked != "— 선택 —":
                parts = [p.strip() for p in picked.split("|")]
                nm = parts[0] if len(parts) > 0 else ""
                sc = parts[1] if len(parts) > 1 else "-"
                cc = parts[2] if len(parts) > 2 else ""

                st.session_state.quick_corp_name = nm
                st.session_state.quick_stock_code = (sc if sc != "-" else "")
                st.session_state.quick_corp_code = cc

                # 업종 자동 추정(사용자가 '자동/미지정'이면 자동으로 바꿔줌)
                if st.session_state.industry_tag in ["자동/미지정", "기타"]:
                    guessed = infer_tag_from_name(nm)
                    if guessed and guessed in INDUSTRY_TAGS:
                        st.session_state.industry_tag = guessed

        # 3) 피어 표(최대 20개)
        if master_q is not None and st.session_state.industry_tag in PEER_NAMES_BY_TAG:
            peer_df = build_peer_table(
                industry_tag=st.session_state.industry_tag,
                master_df=master_q,
                target_ticker6=(st.session_state.quick_stock_code if st.session_state.quick_stock_code else None),
                max_rows=20
            )
            if peer_df is not None and (not peer_df.empty):
                st.markdown("#### 📌 Peer (업종 유사 · 최대 20개)")
                st.dataframe(peer_df, use_container_width=True, height=min(380, 38 + 34 * (len(peer_df) + 1)))
            else:
                st.caption("※ 피어 종목을 찾지 못했습니다(상장/명칭 매칭 문제일 수 있음).")
        else:
            st.caption("※ 업종 태그를 선택하면 해당 업종의 대표 피어가 표로 표시됩니다.")

    # =========================================================
    # ✅ (추가) 사이드바 좌측 하단 고정 Footer
    # =========================================================
    st.markdown(
        """
        <style>
        div[data-testid="stSidebar"] .sidebar-footer {
            margin-top: 18px;
            font-size: 11px;
            line-height: 1.45;
            color: rgba(0,0,0,0.55);
            padding: 8px 10px;
            border-radius: 10px;
            background: rgba(255,255,255,0.6);
            backdrop-filter: blur(6px);
            border: 1px solid rgba(0,0,0,0.06);
        }
        div[data-testid="stSidebar"] .sidebar-footer b { color: rgba(0,0,0,0.75); }
        </style>

        <div class="sidebar-footer">
            <b> 조현규 </b> · 2026.01.15 <br/>
            Data: DART · KRX(pykrx) · BOK ECOS <br/>
            Built with GPT-assisted(+background) <br/>       
            기업 & 밸류에이션 분석용(가벼운) 대시보드 
        </div>
        """,
        unsafe_allow_html=True
    )




# Company search
if search_btn:
    st.session_state.report_ready = False
    st.session_state.company_info = None
    st.session_state.wide = None
    st.session_state.year_to_term = {}
    st.session_state.selected_corp_code = ""
    st.session_state.picked_row_idx = None

    st.session_state.market_ok = False
    st.session_state.market_msg = ""
    st.session_state.mktcap = None
    st.session_state.shares = None
    st.session_state.close = None
    st.session_state.mkt_date = None
    st.session_state.fund = None
    st.session_state.price_df = pd.DataFrame()

    st.session_state.beta_ok = False
    st.session_state.beta_val = None
    st.session_state.beta_msg = ""

    st.session_state.evhist = pd.DataFrame()

    st.session_state.peer_rows = pd.DataFrame()
    st.session_state.peer_ok = False
    st.session_state.peer_msg = ""
    st.session_state.peer_stats = {}
    st.session_state.last_dcf = None

    if not crtfc_key:
        st.error("DART API 키부터 입력하세요.")
    elif not query.strip():
        st.error("회사명/종목코드를 입력하세요.")
    else:
        try:
            with st.spinner("DART 기업 목록(corp master) 불러오는 중..."):
                master = load_corp_master(crtfc_key)
            cand = find_corp_code(master, mode, query)

            if cand.empty:
                st.session_state.corp_candidates = pd.DataFrame()
                st.error("회사 후보를 찾지 못했습니다.")
            else:
                cand = cand[["corp_code", "corp_name", "stock_code"]].reset_index(drop=True)
                st.session_state.corp_candidates = cand
                st.success("회사 후보를 찾았습니다. 아래에서 ‘행 클릭 선택’ 후 [② 재무 가져오기]를 누르세요.")
        except Exception as e:
            st.error(f"불러오기 실패: {e}")

# Candidate UI
if not st.session_state.report_ready:
    cand = st.session_state.corp_candidates
    if cand is None or cand.empty:
        st.info("왼쪽에서 ① 검색 → 후보 선택 → ② 재무 가져오기 순서로 진행하세요.")
    else:
        st.markdown('<div class="section-title">🔎 회사 후보</div>', unsafe_allow_html=True)

        picked = None
        used_click_select = False
        try:
            event = st.dataframe(
                cand,
                use_container_width=True,
                height=320,
                on_select="rerun",
                selection_mode="single-row",
            )
            used_click_select = True
            if hasattr(event, "selection") and event.selection and "rows" in event.selection:
                rows = event.selection["rows"]
                if rows:
                    picked = int(rows[0])
        except TypeError:
            used_click_select = False

        if (not used_click_select) or (picked is None):
            st.caption("※ Streamlit 버전에서 ‘행 클릭 선택’이 지원되지 않아 선택박스로 대체됩니다.")
            c2 = cand.copy()
            c2["stock_code"] = c2["stock_code"].replace("", pd.NA).fillna("-")
            options = (c2["corp_name"] + " | " + c2["stock_code"] + " | " + c2["corp_code"]).tolist()
            pick = st.selectbox("회사 선택", options)
            st.session_state.selected_corp_code = pick.split("|")[-1].strip()
        else:
            st.session_state.picked_row_idx = picked
            st.session_state.selected_corp_code = str(cand.iloc[picked]["corp_code"]).strip()
            st.success(f"선택됨: {cand.iloc[picked]['corp_name']} | {cand.iloc[picked]['stock_code']} | {st.session_state.selected_corp_code}")

# Fetch finance + market
if fetch_btn:
    if not crtfc_key:
        st.error("DART API 키부터 입력하세요.")
    elif not st.session_state.selected_corp_code:
        st.error("먼저 회사 후보를 검색하고, 회사를 선택하세요.")
    else:
        try:
            corp_code = st.session_state.selected_corp_code
            with st.spinner("회사 기본정보(company.json) 가져오는 중..."):
                info = dart_company_info(crtfc_key, corp_code)

            with st.spinner(f"최근 {n_years}년치 주요재무(fnlttSinglAcnt) 가져오는 중..."):
                wide, year_to_term = fetch_last_n_years_wide(
                    crtfc_key=crtfc_key,
                    corp_code=corp_code,
                    end_year=int(end_year),
                    n_years=int(n_years),
                    reprt_code=reprt_code,
                    fs_div=fs_div,
                )
                  

            if wide is None or wide.empty:
                st.warning("재무 데이터가 비어있습니다. (보고서/연결·별도/연도 조합을 바꿔보세요)")
            else:
                # ✅ IS(영업외수익/비용 포함) 재구성해서 저장
                with st.spinner(f"최근 {n_years}년치 IS(영업외수익/비용 포함) 재구성 중..."):
                    wide_is, is_term = fetch_last_n_years_is_items(
                        crtfc_key=crtfc_key,
                        corp_code=corp_code,
                        end_year=int(end_year),
                        n_years=int(n_years),
                        reprt_code=reprt_code,
                        fs_div=fs_div,
                    )
                    st.session_state.wide_is = wide_is
                    if (not year_to_term) and is_term:
                        year_to_term = is_term

                with st.spinner("운전자본(AR/INV/AP) 계정 추출 중..."):
                    wc_bs = fetch_wc_bs_history(
                        crtfc_key=crtfc_key,
                        corp_code=corp_code,
                        end_year=int(end_year),
                        n_years=int(n_years),
                        reprt_code=reprt_code,
                        fs_div=fs_div,
                    )
                    st.session_state.wc_bs = wc_bs

                
                
                sc = info.get("stock_code") or ""
                with st.spinner("KRX 시장데이터(주가/시총/PER/PBR) 연동 중..."):
                    ok, msg = fetch_market_bundle_krx(sc)
                    st.session_state.market_msg = msg

                with st.spinner("EV/EBITDA(연도별) 직접계산 준비 중..."):
                    evh = ev_ebitda_history(crtfc_key, corp_code, _ticker6(sc), int(end_year), int(n_years), reprt_code, fs_div)
                    st.session_state.evhist = evh

                st.session_state.company_info = info
                st.session_state.wide = wide
                st.session_state.year_to_term = year_to_term
                st.session_state.report_ready = True
                st.session_state.page = "0 홈"
                st.session_state.corp_candidates = pd.DataFrame()

                if msg:
                    st.warning(msg)

                st.success("완료! 상단에서 페이지를 선택하세요.")
                st.rerun()

        except Exception as e:
            st.error(f"가져오기 실패: {e}")

# Report screen
if st.session_state.report_ready:
    info = st.session_state.company_info
    wide = st.session_state.wide
    year_to_term = st.session_state.year_to_term or {}
    evhist = st.session_state.evhist

    render_selected_company(info)
    render_top_nav(st.session_state.reprt_code, st.session_state.fs_div)

    unit = st.session_state.unit
    page = st.session_state.page
    industry_tag = st.session_state.industry_tag or "자동/미지정"

    if page == "0 홈":
        render_home()
    elif page == "1 손익(IS)":
        render_is(wide, year_to_term, unit, industry_tag)
    elif page == "2 재무상태(BS)":
        render_bs(wide, year_to_term, unit, industry_tag)
    elif page == "3 시장/멀티플":
        render_market_page(info, wide, evhist)
    elif page == "4 Peer":
        render_peer_bridge(
            crtfc_key=crtfc_key,
            info=info,
            end_year=int(st.session_state.get("sb_end_year", _now_kst().year-1)),
            n_years=int(st.session_state.get("sb_n_years", 5)),
            reprt_code=st.session_state.reprt_code,
            fs_div=st.session_state.fs_div
        )
    elif page == "5 DCF/WACC":
        render_dcf_wacc(info, wide, unit, industry_tag)
    elif page == "6 채권지표":
        render_bond_page()

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
