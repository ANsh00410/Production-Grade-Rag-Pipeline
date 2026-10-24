# ---- Stage 1: build dependencies ----
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps needed for pymupdf / lxml wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Pre-install CPU-only PyTorch so sentence-transformers doesn't pull heavy CUDA binaries
RUN pip install --no-cache-dir --user torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Stage 2: runtime image ----
FROM python:3.11-slim

WORKDIR /app

# Copy only the installed packages, not build tools -> smaller final image
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
