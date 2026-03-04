FROM python:3.11-slim

WORKDIR /app

# Copy source first so editable install (setuptools src layout) can find it
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir -e .

COPY data/ data/

ENV HTTP_HOST=0.0.0.0
ENV HTTP_PORT=8080

EXPOSE 8080

CMD ["uvicorn", "parallelife.apps.api_gateway:app", "--host", "0.0.0.0", "--port", "8080"]
