FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_DEBUG=False
EXPOSE 8080

# Cloud Run injects $PORT (defaults to 8080) - shell form so it expands.
# --worker-class gthread --workers 2 --threads 4: the search page fires two
# requests in parallel on load (campground list + facets); a single sync
# worker (gunicorn's default) serializes them, so the second one waits
# behind the first even after the cold-start cost is already paid. Most of
# each request's time is MongoDB network I/O, not CPU, so threads help more
# than raw worker count here - stays well within the 512Mi memory limit.
CMD python manage.py migrate --run-syncdb --noinput && \
    gunicorn campground_api.wsgi:application --bind 0.0.0.0:${PORT:-8080} \
        --worker-class gthread --workers 2 --threads 4
