FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WAKH_DEBUG=0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 9090

CMD ["sh", "-c", "python manage.py migrate --noinput && uvicorn wakh_server.asgi:application --host 0.0.0.0 --port 9090"]
