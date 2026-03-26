# Use python 3.9 slim (to match your environment)
FROM python:3.9-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Set functional working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy all local project files to the container
COPY . .

# Run the app using Gunicorn (we bind to the Cloud Run standard $PORT)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
