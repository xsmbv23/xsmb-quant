FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
# The runtime forensic bootstrap requires the legacy Excel cache at the
# application root. Copy it explicitly so the data artifact cannot be
# accidentally omitted from the container build context.
COPY Ket_Qua_Loto27.xlsx /app/Ket_Qua_Loto27.xlsx

# Apply the deterministic archive-prize parser patch at image build time.
# The resulting /app/app.py is the exact source hashed by the runtime
# forensic manifest.
COPY build_patch_crawler.py /app/build_patch_crawler.py
COPY build_patch_calendar.py /app/build_patch_calendar.py
RUN python /app/build_patch_crawler.py && python /app/build_patch_calendar.py && rm -f /app/build_patch_crawler.py /app/build_patch_calendar.py

# Render injects PORT at runtime; app.py reads it and binds Gradio to 0.0.0.0.
ENV WEB_CONCURRENCY=1
CMD ["python", "app.py"]
