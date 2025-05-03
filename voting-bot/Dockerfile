FROM python:3.13-alpine

WORKDIR /app

COPY alembic.ini .
COPY alembic/ .
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["sh", "-c", "alembic upgrade head && python main.py"]