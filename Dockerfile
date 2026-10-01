FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Render injects PORT at runtime; app.py reads it and binds Gradio to 0.0.0.0.
ENV WEB_CONCURRENCY=1
CMD ["python", "app.py"]
