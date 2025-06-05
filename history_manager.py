
import os
import pandas as pd
import streamlit as st
from datetime import datetime
from notion_utils import create_customer_record, delete_customer_from_notion

HISTORY_FILE = "ltv_input_history.csv"
ARCHIVE_FILE = "ltv_archive_deleted.xlsx"

def get_customer_options():
    if not os.path.exists(HISTORY_FILE):
        return []
    df = pd.read_csv(HISTORY_FILE)
    return df["고객명"].unique().tolist()

def save_user_input(overwrite=False):
    if "customer_name" not in st.session_state or not st.session_state["customer_name"]:
        return
    name = st.session_state["customer_name"]
    user_data = {
        "고객명": name,
        "주소": st.session_state.get("address_input", ""),
        "지역": st.session_state.get("region", ""),
        "KB시세": st.session_state.get("raw_price_input", ""),
        "면적": st.session_state.get("area_input", ""),
        "공동소유자": st.session_state.get("co_owners", ""),
        "방공제": st.session_state.get("deduction_input", ""),
        "대출항목": st.session_state.get("대출항목", ""),
        "수수료": st.session_state.get("total_fee", ""),
        "컨설팅수수료": st.session_state.get("consult_fee", ""),
        "브릿지수수료": st.session_state.get("bridge_fee", ""),
        "가용자금": st.session_state.get("available_amount", ""),
        "메모": st.session_state.get("memo", ""),
        "저장일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    df_new = pd.DataFrame([user_data])
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        if overwrite:
            df = df[df["고객명"] != name]
        df = pd.concat([df, df_new], ignore_index=True)
    else:
        df = df_new
    df.to_csv(HISTORY_FILE, index=False)

    # ✅ 저장 시 Notion에도 기록 (deleted_at 제거)
    create_customer_record(
        name=user_data["고객명"],
        address=user_data["주소"],
        region=user_data["지역"],
        memo=user_data["메모"],
        loans=str(user_data["대출항목"]),
        kb_price=user_data["KB시세"],
        area=user_data["면적"],
        co_owners=user_data["공동소유자"]
    )

def load_customer_input(name):
    if not os.path.exists(HISTORY_FILE):
        return
    df = pd.read_csv(HISTORY_FILE)
    df_matched = df[df["고객명"] == name]
    if df_matched.empty:
        st.warning(f"⚠️ '{name}'에 해당하는 저장기록이 없습니다.")
        return
    record = df_matched.iloc[-1].to_dict()
    st.session_state["customer_name"] = record.get("고객명", "")
    st.session_state["address_input"] = record.get("주소", "")
    st.session_state["region"] = record.get("지역", "")
    st.session_state["raw_price_input"] = record.get("KB시세", "")
    st.session_state["area_input"] = record.get("면적", "")
    st.session_state["co_owners"] = record.get("공동소유자", "")
    st.session_state["deduction_input"] = record.get("방공제", "")
    st.session_state["대출항목"] = eval(record.get("대출항목", "[]"))
    st.session_state["total_fee"] = record.get("수수료", "")
    st.session_state["consult_fee"] = record.get("컨설팅수수료", "")
    st.session_state["bridge_fee"] = record.get("브릿지수수료", "")
    st.session_state["available_amount"] = record.get("가용자금", "")
    st.session_state["memo"] = record.get("메모", "")

def cleanup_old_history(name_to_delete):
    if not os.path.exists(HISTORY_FILE):
        return
    df = pd.read_csv(HISTORY_FILE)
    deleted_df = df[df["고객명"] == name_to_delete]
    df = df[df["고객명"] != name_to_delete]
    df.to_csv(HISTORY_FILE, index=False)
    if not deleted_df.empty:
        deleted_df["삭제일시"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if os.path.exists(ARCHIVE_FILE):
            archive_df = pd.read_excel(ARCHIVE_FILE)
            archive_df = pd.concat([archive_df, deleted_df], ignore_index=True)
        else:
            archive_df = deleted_df
        archive_df.to_excel(ARCHIVE_FILE, index=False)
        st.session_state["deleted_data_ready"] = True

        # ✅ Notion에 삭제 기록도 반영
        delete_customer_from_notion(name_to_delete)

def search_customers_by_keyword(keyword):
    if not os.path.exists(HISTORY_FILE):
        return []
    df = pd.read_csv(HISTORY_FILE)
    matches = df[df["고객명"].str.contains(keyword, na=False)]["고객명"].unique().tolist()
    return matches
