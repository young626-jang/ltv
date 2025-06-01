from notion_client import Client
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import os

HISTORY_FILE = "ltv_input_history.csv"
ARCHIVE_FILE = "ltv_archive_deleted.xlsx"


def auto_delete_old_entries_from_notion(days=30):
    """30일 이상 된 고객 데이터를 Notion에서 자동 archive 처리"""
    try:
        notion = Client(auth=st.secrets["notion"]["token"])
        db_id = st.secrets["notion"]["database_id"]

        response = notion.databases.query(database_id=db_id)
        results = response.get("results", [])
        cutoff = datetime.now() - timedelta(days=days)

        for page in results:
            props = page.get("properties", {})
            text = props.get("저장시각", {}).get("rich_text", [])
            if not text:
                continue

            time_str = text[0]["text"]["content"]

            try:
                saved_at = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                if saved_at < cutoff:
                    notion.pages.update(page_id=page["id"], archived=True)
            except Exception as e:
                st.warning(f"날짜 파싱 실패: {e}")
    except Exception as e:
        st.error(f"❌ Notion 자동 삭제 실패: {e}")


def delete_customer_everywhere(name_to_delete: str):
    """고객명을 기반으로 CSV와 Notion에서 동시 삭제"""
    # ✅ 1. CSV에서 삭제 + 백업 저장
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        to_delete = df[df["고객명"] == name_to_delete]
        df = df[df["고객명"] != name_to_delete]

        if not to_delete.empty:
            to_delete.to_excel(ARCHIVE_FILE, index=False)
            st.session_state["deleted_data_ready"] = True

        df.to_csv(HISTORY_FILE, index=False)

    # ✅ 2. Notion에서 해당 고객명을 가진 row 찾아 archive
    try:
        notion = Client(auth=st.secrets["notion"]["token"])
        db_id = st.secrets["notion"]["database_id"]

        response = notion.databases.query(
            database_id=db_id,
            filter={
                "property": "고객명",
                "title": {
                    "contains": name_to_delete
                }
            }
        )
        for page in response.get("results", []):
            notion.pages.update(page_id=page["id"], archived=True)
    except Exception as e:
        st.warning(f"⚠️ Notion 삭제 중 오류 발생: {e}")
