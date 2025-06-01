# notion_utils.py
from notion_client import Client
from datetime import datetime, timedelta
import streamlit as st

notion = Client(auth=st.secrets["notion"]["token"])
db_id = st.secrets["notion"]["database_id"]

def delete_customer_from_notion(customer_name):
    response = notion.databases.query(
        database_id=db_id,
        filter={"property": "고객명", "rich_text": {"equals": customer_name}}
    )
    for result in response.get("results", []):
        notion.pages.update(page_id=result["id"], archived=True)

def auto_delete_old_entries_from_notion(days=30):
    cutoff = datetime.now() - timedelta(days=days)
    response = notion.databases.query(database_id=db_id)

    for result in response.get("results", []):
        props = result["properties"]
        field = props.get("저장시각", {}).get("rich_text", [])
        if field:
            try:
                dt = datetime.strptime(field[0]["plain_text"], "%Y-%m-%d %H:%M:%S")
                if dt < cutoff:
                    notion.pages.update(page_id=result["id"], archived=True)
            except:
                continue
