# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the python script into the container
COPY mc_cleaner.py .

# REMOVED EXPOSE 3000 - Render handles port routing dynamically via environment variables

# Run the script when the container starts
CMD ["python", "mc_cleaner.py"]

