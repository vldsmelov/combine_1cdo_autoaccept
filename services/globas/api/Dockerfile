# syntax=docker/dockerfile:1.7
FROM company/python-api-base:3.11

WORKDIR /app

RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt,ro \
    --mount=type=cache,target=/root/.cache/pip \
    pip install -r /tmp/requirements.txt

COPY . /app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
