FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY tests/ ./tests/
COPY examples/ ./examples/
COPY pytest.ini ./

CMD ["python", "-m", "pytest", "tests/test_harness.py", "-v"]
