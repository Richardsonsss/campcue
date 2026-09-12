FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_DEBUG=False
EXPOSE 8080

# Cloud Run injects $PORT (defaults to 8080) - shell form so it expands.
CMD python manage.py migrate --run-syncdb --noinput && \
    gunicorn campground_api.wsgi:application --bind 0.0.0.0:${PORT:-8080}
