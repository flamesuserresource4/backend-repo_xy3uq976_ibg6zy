from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId

MONGO_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DATABASE_NAME", "appdb")

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None


def get_db() -> AsyncIOMotorDatabase:
    global client, db
    if db is None:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
    return db


def to_object_id(id_str: str) -> ObjectId:
    return ObjectId(id_str)


async def create_document(collection_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    database = get_db()
    data = {**data, "created_at": data.get("created_at"), "updated_at": data.get("updated_at")}
    result = await database[collection_name].insert_one(data)
    inserted = await database[collection_name].find_one({"_id": result.inserted_id})
    return normalize_id(inserted)


async def get_documents(
    collection_name: str,
    filter_dict: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    database = get_db()
    cursor = database[collection_name].find(filter_dict or {})
    if limit:
        cursor = cursor.limit(limit)
    docs = [normalize_id(doc) async for doc in cursor]
    return docs


def normalize_id(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id"))
    return doc
