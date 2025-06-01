from notion_client import Client
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import os

HISTORY_FILE = "ltv_input_history.csv"
ARCHIVE_FILE = "ltv_archive_deleted.xlsx"


def auto_delete_old_entries_from_notion(days=30):
    """
    Notion DB에서 30일 이상 지난 고객 정보를 자동으로 archive 처리
    """
    try:
        notion = Client(auth=st.secrets["notion"]["token"])
        db_id = st.secrets["notion"]["database_id"]

        response = notion.databases.query(database_id=db_id)
        results = response.get("results", [])

        cutoff = datetime.now() - timedelta(days=days)

        for page in results:
            props = page.get("properties", {})
            time_field = props.get("저장시각", {}).get("rich_text", [])
            if not time_field:
                continue

            try:
                time_str = time_field[0]["text"]["content"]
                saved_at = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                if saved_at < cutoff:
                    notion.pages.update(page_id=page["id"], archived=True)
            except Exception:
                # 한글 등 인코딩 이슈가 있는 경우에도 무시하고 계속 진행
                continue

    except Exception as e:
        st.error("❌ Notion 자동 삭제 실패. secrets.toml 설정 또는 DB 포맷 확인 필요")


def delete_customer_everywhere(name_to_delete: str):
    """
    고객명을 기준으로 CSV와 Notion DB에서 동시에 삭제 (Notion은 archive)
    """
    # ✅ 1. CSV에서 삭제 및 백업 저장
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        to_delete = df[df["고객명"] == name_to_delete]
        df = df[df["고객명"] != name_to_delete]

        if not to_delete.empty:
            to_delete.to_excel(ARCHIVE_FILE, index=False)
            st.session_state["deleted_data_ready"] = True

        df.to_csv(HISTORY_FILE, index=False)

    # ✅ 2. Notion에서 고객명으로 archive
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
        st.warning("⚠️ Notion 고객 삭제 중 오류 발생 (token, database_id, 속성명 확인 필요)")
