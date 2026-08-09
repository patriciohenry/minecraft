# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the python script into the container
COPY mc_cleaner.py .

# CRITICAL FIX: Tell Render to route public internet traffic to port 3000
EXPOSE 3000

# Run the script when the container starts
CMD ["python", "mc_cleaner.py"]

