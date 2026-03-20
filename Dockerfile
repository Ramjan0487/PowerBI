FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libgl1 libglib2.0-0 libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS production
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libpq5 curl && rm -rf /var/lib/apt/lists/* && addgroup --system cms && adduser --system --ingroup cms cms
COPY --from=builder /install /usr/local
COPY --chown=cms:cms . .
RUN mkdir -p /app/uploads && chown cms:cms /app/uploads
USER cms
EXPOSE 5000
ENV FLASK_ENV=production PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
CMD ["gunicorn","wsgi:app","--bind","0.0.0.0:5000","--workers","4","--timeout","60","--access-logfile","-"]

FROM production AS test
USER root
RUN pip install --no-cache-dir pytest pytest-cov pytest-flask faker
USER cms
ENV FLASK_ENV=testing
CMD ["pytest","tests/","-v","--tb=short","--cov=app","--cov-report=term-missing"]
