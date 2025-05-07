FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 시스템 의존성 설치 (weasyprint 요구사항 + curl 추가)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libxml2 \
    libffi-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"


# pyproject.toml 복사
COPY pyproject.toml ./

# uv로 의존성 설치
RUN uv pip install --system -e .

# 폰트 디렉토리 생성 및 폰트 파일 복사
RUN mkdir -p /app/fonts
COPY fonts/ /app/fonts/

# 애플리케이션 코드 복사
COPY app/ /app

# 출력 디렉토리 생성
RUN mkdir -p /app/outputs

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV PORT=8000

# FastAPI 서버 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app"]

# 포트 노출
EXPOSE 8000
