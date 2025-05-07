from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import logging
import random
import string

from datetime import datetime

from services.boj_service import BojService
from services.random_problems import generate_random_problems

from database.models import get_db
from database.task_repository import TaskRepository
from sqlalchemy.orm import Session


# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BOJ PDF Generator",
    description="백준 온라인 저지 문제를 PDF로 변환하는 API",
    version="1.0.0"
)

# 결과 파일을 저장할 디렉토리
OUTPUT_DIR = "./outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 현재 실행 중인 작업 추적
running_tasks = {}


class ProblemSet(BaseModel):
    problems: List[int]


class ProblemRequest(BaseModel):
    problems_per_set: int = 4
    min_problem_id: int = 1000
    max_problem_id: int = 20000
    username: Optional[str] = "singun11"


@app.get("/")
async def root():
    return {"message": "BOJ PDF Generator API"}


@app.post("/generate-random-problems")
async def create_random_problems(request: ProblemRequest):
    """랜덤 문제 세트 생성"""
    try:
        problem_set = generate_random_problems(
            count=request.problems_per_set,
            username=request.username,
            min_problem_id=request.min_problem_id,
            max_problem_id=request.max_problem_id
        )

        return {"problem_set": problem_set}
    except Exception as e:
        logger.error(f"Error generating random problems: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-pdf")
async def generate_pdf(problem_set: ProblemSet, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """문제 세트를 PDF로 변환 (비동기 작업)"""
    task_id = str(uuid.uuid4())

    # 현재 날짜로 된 파일 이름 생성
    today_str = datetime.today().strftime('%Y-%m-%d')
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    output_filename = f"{today_str}_{random_suffix}.pdf"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    TaskRepository.create_task(
        db=db,
        task_id=task_id,
        status="running",
        output_file=output_path,
        filename=output_filename
    )
    db.commit()

    # 백그라운드 작업으로 PDF 생성
    background_tasks.add_task(
        process_pdf_generation,
        task_id,
        problem_set.problems,
        output_path,
        db
    )

    return {
        "task_id": task_id,
        "status": "running",
        "message": "PDF 생성이 시작되었습니다."
    }


@app.get("/task/{task_id}")
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """작업 상태 확인"""
    task = TaskRepository.get_task(db, task_id)
    if not task:
        # 200 OK 상태로 태스크가 없음을 알림
        return {
            "task_id": task_id,
            "status": "not_found",
            "message": "Task not found"
        }

    return {
        "task_id": task.id,
        "status": task.status,
        "output_file": task.output_file,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "filename": task.filename,
        "error": task.error
    }


@app.get("/download/{task_id}")
async def download_pdf(task_id: str, db: Session = Depends(get_db)):
    """생성된 PDF 다운로드"""
    task = TaskRepository.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="PDF generation not completed yet")

    output_file = task.output_file
    if not os.path.exists(output_file):
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        path=output_file,
        filename=os.path.basename(output_file),
        media_type="application/pdf"
    )

async def process_pdf_generation(task_id, problems, output_path, db: Session = Depends(get_db)):
    """백그라운드에서 PDF 생성 처리"""
    try:
        service = BojService()
        await service.generate_pdf(problems, output_path)

        # 태스크 상태 업데이트
        TaskRepository.update_task_status(db, task_id, "completed")
        logger.info(f"PDF generation completed for task {task_id}")
    except Exception as e:
        # 태스크 상태 업데이트 (에러)
        TaskRepository.update_task_status(db, task_id, "failed", str(e))
        logger.error(f"PDF generation failed for task {task_id}: {str(e)}")