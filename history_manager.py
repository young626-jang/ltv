import pandas as pd
import os
from datetime import datetime
import streamlit as st
from ast import literal_eval
from notion_utils import delete_customer_from_notion  # 추가됨

HISTORY_FILE = "ltv_input_history.csv"
ARCHIVE_FILE = "ltv_archive_deleted.xlsx"

def get_customer_name():
    return st.session_state.get("customer_name", "").strip()

def get_customer_options():
    if not os.path.exists(HISTORY_FILE):
        return []
    df = pd.read_csv(HISTORY_FILE)
    if df.empty:
        return []
    return df["고객명"].dropna().unique().tolist()

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

    # ✅ 메모 필드 복원
    st.session_state["memo_input"] = record.get("메모", "")

def save_user_input(overwrite=False):
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
        "메모": st.session_state.get("memo_input", ""),  # ✅ 메모 저장
        "저장시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

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

    if os.path.exists(HISTORY_FILE):
        df_old = pd.read_csv(HISTORY_FILE)
        if overwrite:
            df_old = df_old[df_old["고객명"] != customer_name]
        df_final = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_final = df_new

    df_final.to_csv(HISTORY_FILE, index=False)

def cleanup_old_history(name_to_delete):
    if not os.path.exists(HISTORY_FILE):
        return

    df = pd.read_csv(HISTORY_FILE)
    to_delete = df[df["고객명"] == name_to_delete]
    df = df[df["고객명"] != name_to_delete]

    if not to_delete.empty:
        to_delete.to_excel(ARCHIVE_FILE, index=False)
        st.session_state["deleted_data_ready"] = True

    df.to_csv(HISTORY_FILE, index=False)

def search_customers_by_keyword(keyword):
    if not os.path.exists(HISTORY_FILE):
        return []
    df = pd.read_csv(HISTORY_FILE)
    results = df[df["고객명"].str.contains(keyword, na=False)]
    return results["고객명"].unique().tolist()
