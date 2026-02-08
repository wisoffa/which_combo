# Use an official lightweight Python image.
FROM python:3.9-slim

# Set the working directory in the container.
WORKDIR /app

# Copy the dependencies file and install them.
# This is done as a separate step to take advantage of Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container.
COPY . .

# Expose the port that Gunicorn will run on.
# Cloud Run provides the PORT environment variable, defaulting to 8080.
EXPOSE 8080

# Command to run the application using a production-grade server.
# Gunicorn is a process manager, and it will use Uvicorn workers for ASGI.
# It listens on all interfaces (0.0.0.0) on the port specified by the PORT env var.
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8080", "server:app"]
