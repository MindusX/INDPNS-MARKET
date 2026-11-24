FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=config.settings.production
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x docker-entrypoint.sh \
 && python scripts/compile_po.py \
 && SECRET_KEY=build-only-not-used-at-runtime python manage.py collectstatic --noinput
CMD ["./docker-entrypoint.sh"]
