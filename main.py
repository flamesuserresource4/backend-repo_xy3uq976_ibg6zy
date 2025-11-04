from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId

from database import get_db, normalize_id
from database import create_document, get_documents
from schemas import Project, ProjectUpdate, Testcase, TestcaseUpdate, Plan

app = FastAPI(title="QA Task Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "QA Task Manager API is running"}


@app.get("/test")
async def test_connection() -> Dict[str, Any]:
    db = get_db()
    # Ensure plan doc exists
    plan_doc = await db["plan"].find_one({})
    if not plan_doc:
        await db["plan"].insert_one({"plan": "free"})
        plan_doc = await db["plan"].find_one({})

    collections = await db.list_collection_names()
    return {
        "backend": "fastapi",
        "database": "mongo",
        "database_url": "env",
        "database_name": db.name,
        "connection_status": "ok",
        "collections": collections,
        "plan": plan_doc.get("plan"),
    }


# Plan endpoints
@app.get("/plan")
async def get_plan() -> Dict[str, str]:
    db = get_db()
    plan_doc = await db["plan"].find_one({})
    if not plan_doc:
        await db["plan"].insert_one({"plan": "free"})
        plan_doc = await db["plan"].find_one({})
    return {"plan": plan_doc.get("plan", "free")}


@app.post("/plan/upgrade")
async def upgrade_plan() -> Dict[str, str]:
    db = get_db()
    await db["plan"].update_one({}, {"$set": {"plan": "pro"}}, upsert=True)
    return {"plan": "pro"}


# Project CRUD
@app.get("/projects")
async def list_projects() -> List[Dict[str, Any]]:
    docs = await get_documents("project")
    return docs


@app.post("/projects")
async def create_project(project: Project) -> Dict[str, Any]:
    db = get_db()
    plan_doc = await db["plan"].find_one({})
    plan = (plan_doc or {}).get("plan", "free")

    existing_count = await db["project"].count_documents({})
    if plan == "free" and existing_count >= 1:
        raise HTTPException(status_code=402, detail="Free plan allows only 1 project. Upgrade to Pro for unlimited projects.")

    inserted = await create_document("project", project.model_dump())
    return inserted


@app.put("/projects/{project_id}")
async def update_project(project_id: str, payload: ProjectUpdate) -> Dict[str, Any]:
    db = get_db()
    try:
        oid = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project id")
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No changes provided")
    res = await db["project"].find_one_and_update({"_id": oid}, {"$set": update_data}, return_document=True)
    if not res:
        raise HTTPException(status_code=404, detail="Project not found")
    return normalize_id(res)


@app.delete("/projects/{project_id}")
async def delete_project(project_id: str) -> Dict[str, str]:
    db = get_db()
    try:
        oid = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project id")
    # Cascade delete testcases
    await db["testcase"].delete_many({"project_id": project_id})
    res = await db["project"].delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "deleted"}


# Testcase operations
@app.get("/projects/{project_id}/testcases")
async def list_testcases(project_id: str) -> List[Dict[str, Any]]:
    docs = await get_documents("testcase", {"project_id": project_id})
    return docs


@app.post("/projects/{project_id}/testcases")
async def create_testcase(project_id: str, payload: Testcase) -> Dict[str, Any]:
    if project_id != payload.project_id:
        raise HTTPException(status_code=400, detail="Project id mismatch")
    inserted = await create_document("testcase", payload.model_dump())
    return inserted


@app.put("/testcases/{testcase_id}")
async def update_testcase(testcase_id: str, payload: TestcaseUpdate) -> Dict[str, Any]:
    db = get_db()
    try:
        oid = ObjectId(testcase_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid testcase id")
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No changes provided")
    res = await db["testcase"].find_one_and_update({"_id": oid}, {"$set": update_data}, return_document=True)
    if not res:
        raise HTTPException(status_code=404, detail="Testcase not found")
    return normalize_id(res)


@app.delete("/testcases/{testcase_id}")
async def delete_testcase(testcase_id: str) -> Dict[str, str]:
    db = get_db()
    try:
        oid = ObjectId(testcase_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid testcase id")
    res = await db["testcase"].delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Testcase not found")
    return {"status": "deleted"}


@app.get("/dashboard")
async def dashboard() -> Dict[str, Any]:
    db = get_db()
    total_projects = await db["project"].count_documents({})
    total_testcases = await db["testcase"].count_documents({})
    pass_count = await db["testcase"].count_documents({"status": "Pass"})
    fail_count = await db["testcase"].count_documents({"status": "Fail"})
    pending_count = await db["testcase"].count_documents({"status": "Pending"})

    pass_rate = (pass_count / total_testcases * 100) if total_testcases else 0
    fail_rate = (fail_count / total_testcases * 100) if total_testcases else 0

    return {
        "total_projects": total_projects,
        "total_testcases": total_testcases,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pending_count": pending_count,
        "pass_rate": round(pass_rate, 1),
        "fail_rate": round(fail_rate, 1),
    }
