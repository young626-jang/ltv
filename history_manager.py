import pandas as pd
import os
from datetime import datetime
import streamlit as st
from ast import literal_eval
from notion_utils import delete_customer_from_notion

# 🔧 파일 경로
HISTORY_FILE = "ltv_input_history.csv"
ARCHIVE_FILE = "ltv_archive_deleted.xlsx"


# ───────────────────────────────
# 🔹 기본 도우미 함수
# ───────────────────────────────

def get_customer_name():
    return st.session_state.get("customer_name", "").strip()


def get_customer_options():
    if not os.path.exists(HISTORY_FILE):
        return []
    df = pd.read_csv(HISTORY_FILE)
    if df.empty:
        return []
    return df["고객명"].dropna().unique().tolist()


def search_customers_by_keyword(keyword):
    if not os.path.exists(HISTORY_FILE):
        return []
    df = pd.read_csv(HISTORY_FILE)
    results = df[df["고객명"].str.contains(keyword, na=False)]
    return results["고객명"].unique().tolist()


# ───────────────────────────────
# 📥 고객 불러오기
# ───────────────────────────────

def load_customer_input(customer_name):
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

    # ✅ 예전 데이터 호환: '진행' 필드를 '진행구분'으로 변환
    if "대출항목" in st.session_state:
        normalized_items = []
        for item in st.session_state.get("대출항목", []):
            if isinstance(item, dict):
                if "진행" in item and "진행구분" not in item:
                    item["진행구분"] = item.pop("진행")
            normalized_items.append(item)
        st.session_state["대출항목"] = normalized_items

    st.session_state["memo_input"] = record.get("메모", "")


# ───────────────────────────────
# 💾 고객 저장
# ───────────────────────────────

def save_user_input(overwrite=False):
    customer_name = get_customer_name()
    if not customer_name:
        return

    data = {
        "고객명": customer_name,
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

    rows = int(st.session_state.get("rows", 0))
    for i in range(rows):
        item = {
            "설정자": st.session_state.get(f"lender_{i}", ""),
            "채권최고액": st.session_state.get(f"maxamt_{i}", ""),
            "비율": st.session_state.get(f"ratio_{i}", ""),
            "원금": st.session_state.get(f"principal_{i}", ""),
            "진행구분": st.session_state.get(f"status_{i}", ""),
        }
        data["대출항목"].append(item)

    df_new = pd.DataFrame([data])

    if os.path.exists(HISTORY_FILE):
        df_old = pd.read_csv(HISTORY_FILE)
        if overwrite:
            df_old = df_old[df_old["고객명"] != customer_name]
        df_final = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_final = df_new

    df_final.to_csv(HISTORY_FILE, index=False)


# ───────────────────────────────
# 🧾 삭제 백업만 따로 (옵션)
# ───────────────────────────────

def cleanup_old_history(name_to_delete):
    if not os.path.exists(HISTORY_FILE):
        return

    df = pd.read_csv(HISTORY_FILE)
    to_delete = df[df["고객명"] == name_to_delete]
    df = df[df["고객명"] != name_to_delete]

    if not to_delete.empty:
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

    df.to_csv(HISTORY_FILE, index=False)


# ───────────────────────────────
# 🗑️ 전체 삭제 로직 (Notion + CSV + 백업)
# ───────────────────────────────

def delete_customer_everywhere(customer_name: str):
    if not os.path.exists(HISTORY_FILE):
        st.error("❌ 고객 데이터 파일이 존재하지 않습니다.")
        return

    df = pd.read_csv(HISTORY_FILE)
    to_delete = df[df["고객명"] == customer_name]
    df_remaining = df[df["고객명"] != customer_name]

    if to_delete.empty:
        st.warning(f"⚠️ '{customer_name}'에 해당하는 고객 데이터가 없습니다.")
        return

    # 백업
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

    # Notion에도 기록
    for _, row in to_delete.iterrows():
        try:
            delete_customer_from_notion(
                name=row.get("고객명", ""),
                address=row.get("주소", ""),
                deleted_at=datetime.now().isoformat(),
                region=row.get("지역", ""),
                memo=row.get("메모", ""),
                loans=str(row.get("대출항목", "")),
                kb_price=row.get("KB시세", ""),
                area=row.get("면적", ""),
                co_owners=str(row.get("공동소유자", ""))
            )
        except Exception as e:
            st.warning(f"⚠️ Notion 기록 실패: {e}")

    df_remaining.to_csv(HISTORY_FILE, index=False)
    st.success(f"✅ '{customer_name}' 고객이 삭제되어 기록되었습니다.")
