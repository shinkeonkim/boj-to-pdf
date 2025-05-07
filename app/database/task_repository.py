from sqlalchemy.orm import Session
from .models import Task
from datetime import datetime
import json

class TaskRepository:
    @staticmethod
    def create_task(db: Session, task_id: str, status: str, output_file: str, filename: str):
        """새 태스크를 생성하고 저장"""
        db_task = Task(
            id=task_id,
            status=status,
            output_file=output_file,
            filename=filename,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return db_task

    @staticmethod
    def get_task(db: Session, task_id: str):
        """태스크 ID로 태스크 조회"""
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def update_task_status(db: Session, task_id: str, status: str, error: str = None):
        """태스크 상태 업데이트"""
        db_task = db.query(Task).filter(Task.id == task_id).first()
        if db_task:
            db_task.status = status
            db_task.updated_at = datetime.now()
            if error:
                db_task.error = error
            db.commit()
            db.refresh(db_task)
        return db_task
