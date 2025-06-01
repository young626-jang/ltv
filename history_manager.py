import pandas as pd
import os
from datetime import datetime
import streamlit as st
from ast import literal_eval
from notion_utils import delete_customer_from_notion  # ✅ Notion 기록용 함수

# 🔧 파일 경로 상수
HISTORY_FILE = "ltv_input_history.csv"
ARCHIVE_FILE = "ltv_archive_deleted.xlsx"


# ──────────────────────────────────────────────
# 🔹 고객 기본 정보 및 선택 관련
# ──────────────────────────────────────────────

def get_customer_name():
    """현재 세션에서 입력된 고객명 반환"""
    return st.session_state.get("customer_name", "").strip()


def get_customer_options():
    """CSV 파일에서 유효한 고객명 리스트 추출"""
    if not os.path.exists(HISTORY_FILE):
        return []
    df = pd.read_csv(HISTORY_FILE)
    if df.empty:
        return []
    return df["고객명"].dropna().unique().tolist()


def search_customers_by_keyword(keyword):
    """고객명 키워드 검색"""
    if not os.path.exists(HISTORY_FILE):
        return []
    df = pd.read_csv(HISTORY_FILE)
    results = df[df["고객명"].str.contains(keyword, na=False)]
    return results["고객명"].unique().tolist()


# ──────────────────────────────────────────────
# 🔹 고객 데이터 로딩 및 저장
# ──────────────────────────────────────────────

def load_customer_input(customer_name):
    """고객명 기준으로 최근 입력 이력을 세션에 로딩"""
    if not os.path.exists(HISTORY_FILE):
        return

    df = pd.read_csv(HISTORY_FILE)
    row = df[df["고객명"] == customer_name].tail(1)
    if row.empty:
        return

    record = row.iloc[0].to_dict()

    for key, val in record.items():
        if isinstance(val, str) and val.startswith("[") and val.endswith("]"):
            try:
                val = literal_eval(val)
            except:
                pass
        st.session_state[key] = val

    # ✅ 메모 필드 복원
    st.session_state["memo_input"] = record.get("메모", "")


def save_user_input(overwrite=False):
    """현재 세션 정보를 CSV에 저장"""
    customer_name = get_customer_name()
    if not customer_name:
        return

    data = {
        "고객명": st.session_state.get("customer_name", ""),
        "주소": st.session_state.get("address_input", ""),
        "지역": st.session_state.get("region", ""),
        "방공제": st.session_state.get("manual_d", ""),
        "KB시세": st.session_state.get("raw_price_input", ""),
        "면적": st.session_state.get("area_input", ""),
        "공동소유자": st.session_state.get("co_owners", []),
        "대출항목": [],
        "메모": st.session_state.get("memo_input", ""),
        "저장시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 🔸 대출항목 리스트 구성
    rows = int(st.session_state.get("rows", 0))
    for i in range(rows):
        item = {
            "설정자": st.session_state.get(f"lender_{i}", ""),
            "채권최고액": st.session_state.get(f"maxamt_{i}", ""),
            "비율": st.session_state.get(f"ratio_{i}", ""),
            "원금": st.session_state.get(f"principal_{i}", ""),
            "진행": st.session_state.get(f"status_{i}", ""),
        }
        data["대출항목"].append(item)

    df_new = pd.DataFrame([data])

    # 🔸 기존 CSV에 병합 또는 덮어쓰기
    if os.path.exists(HISTORY_FILE):
        df_old = pd.read_csv(HISTORY_FILE)
        if overwrite:
            df_old = df_old[df_old["고객명"] != customer_name]
        df_final = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_final = df_new

    df_final.to_csv(HISTORY_FILE, index=False)


# ──────────────────────────────────────────────
# 🔹 고객 삭제 로직 (CSV + 엑셀 백업 + Notion 기록)
# ──────────────────────────────────────────────

def cleanup_old_history(name_to_delete):
    """고객 데이터를 HISTORY_FILE에서 제거하고 백업 및 Notion 기록"""
    if not os.path.exists(HISTORY_FILE):
        return

    df = pd.read_csv(HISTORY_FILE)
    to_delete = df[df["고객명"] == name_to_delete]
    df_remaining = df[df["고객명"] != name_to_delete]

    if not to_delete.empty:
        # 🔸 삭제 백업 저장
        if os.path.exists(ARCHIVE_FILE):
            try:
                archive_df = pd.read_excel(ARCHIVE_FILE)
                archive_df = pd.concat([archive_df, to_delete], ignore_index=True)
            except:
                archive_df = to_delete
        else:
            archive_df = to_delete

        archive_df.to_excel(ARCHIVE_FILE, index=False)
        st.session_state["deleted_data_ready"] = True

        # 🔸 Notion 기록 전송
        for _, row in to_delete.iterrows():
            name = row.get("고객명", "")
            address = row.get("주소", "")
            deleted_at = datetime.now().isoformat()
            try:
                delete_customer_from_notion(name=name, address=address, deleted_at=deleted_at)
            except Exception as e:
                st.warning(f"⚠️ Notion 전송 실패: {e}")

    # 🔸 CSV 업데이트
    df_remaining.to_csv(HISTORY_FILE, index=False)
