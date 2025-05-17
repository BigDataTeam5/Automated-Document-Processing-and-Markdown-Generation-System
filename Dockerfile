# Use an official Python image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the entire project to the container
COPY api /app/api
COPY PDF_Extraction_and_Markdown_Generation /app/PDF_Extraction_and_Markdown_Generation
COPY WebScraping_Extraction_and_Markdown_Generation /app/WebScraping_Extraction_and_Markdown_Generation

# Upgrade pip, setuptools, and wheel
RUN pip install --upgrade pip setuptools wheel

# Install backend (API) dependencies
WORKDIR /app/api
RUN pip install --no-cache-dir --upgrade --prefer-binary --use-deprecated=legacy-resolver -r requirements.txt

# Expose the default port for FastAPI
EXPOSE 8080

# Set the working directory back to API before running FastAPI
WORKDIR /app/api

# Start FastAPI with auto-reload for development
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]


