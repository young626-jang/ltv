# notion_utils.py

from notion_client import Client
import os
from datetime import datetime, timedelta
import streamlit as st  # st.secrets용


# 🔐 Notion 클라이언트 초기화 함수
def get_notion_client():
    try:
        token = (
            os.getenv("NOTION_TOKEN")
            or (st.secrets["notion"]["token"] if "notion" in st.secrets else None)
        )
        db_id = (
            os.getenv("NOTION_DB_ID")
            or (st.secrets["notion"]["database_id"] if "notion" in st.secrets else None)
        )
        if not token or not db_id:
            raise Exception("Notion 토큰 또는 DB ID 누락")
        return Client(auth=token), db_id
    except Exception as e:
        raise RuntimeError(f"❌ Notion 설정 로딩 실패: {e}")


# ✅ 고객 삭제 정보 Notion에 기록
def delete_customer_from_notion(
    name,
    address,
    deleted_at,
    region=None,
    memo=None,
    loans=None,
    kb_price=None,
    area=None,
    co_owners=None,
):
    client, database_id = get_notion_client()

    try:
        client.pages.create(
            parent={"database_id": database_id},
            properties={
                "고객명": {"title": [{"text": {"content": name}}]},
                "주소": {"rich_text": [{"text": {"content": address}}]},
                "지역": {"rich_text": [{"text": {"content": region or ""}}]},
                "메모": {"rich_text": [{"text": {"content": memo or ""}}]},
                "대출항목": {"rich_text": [{"text": {"content": loans or ""}}]},
                "KB시세": {
                    "number": float(kb_price) if kb_price not in [None, ""] else 0
                },
                "면적": {"number": float(area) if area not in [None, ""] else 0},
                "공동소유자": {
                    "rich_text": [{"text": {"content": co_owners or ""}}]
                },
                "저장시간": {"date": {"start": deleted_at}},
            },
        )
    except Exception as e:
        raise RuntimeError(f"❌ Notion 기록 실패: {e}")


# ✅ 수동 저장용 Notion 기록 함수 (필요시)
def create_customer_record(
    name,
    address,
    timestamp,
    region="",
    memo="",
    loans="",
    kb_price=0,
    area=0,
    co_owners="",
):
    delete_customer_from_notion(
        name=name,
        address=address,
        deleted_at=timestamp,
        region=region,
        memo=memo,
        loans=loans,
        kb_price=kb_price,
        area=area,
        co_owners=co_owners,
    )


# ✅ 오래된 Notion 항목 자동 archive 기능
def auto_delete_old_entries_from_notion(days=30):
    client, db_id = get_notion_client()
    cutoff = datetime.now() - timedelta(days=days)

    pages = client.databases.query(database_id=db_id).get("results", [])
    
    for page in pages:
        props = page["properties"]
        date_field = props.get("저장시간", {}).get("date", {})
        date_str = date_field.get("start")

        if date_str:
            try:
                page_date = datetime.fromisoformat(date_str)
                if page_date < cutoff:
                    client.pages.update(page["id"], archived=True)
                    print(f"✅ 오래된 레코드 아카이브됨: {props['고객명']['title'][0]['text']['content']}")
            except Exception as e:
                print(f"❌ 날짜 파싱/아카이브 실패: {e}")
