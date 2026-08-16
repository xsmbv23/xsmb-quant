FROM python:3.12-slim
WORKDIR /app
COPY . /app
EXPOSE 10000
CMD ["python", "foundation_gate.py"]
