FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists*

COPY pyproject.toml README.md app.py poetry.lock* ./

RUN pip install poetry

RUN poetry config virtualenvs.create false

RUN poetry install

ENV PYTHONUNBUFFERED=1

CMD ["poetry", "run", "service-run"]
