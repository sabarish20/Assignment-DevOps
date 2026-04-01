FROM python:3.11-slim AS builder

WORKDIR /install

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/deps -r requirements.txt

FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=builder /deps /usr/local

COPY app.py config.py ./

COPY templates/ ./templates/

EXPOSE 8080

RUN useradd --no-create-home appuser

USER appuser

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "2", "app:create_app()"]
