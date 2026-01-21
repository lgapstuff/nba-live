FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY run.py .

# Set Flask app
ENV FLASK_APP=app.main:create_app

# Expose port
ARG APP_PORT=8002
EXPOSE ${APP_PORT}

# Run Flask application
CMD ["python", "run.py"]
