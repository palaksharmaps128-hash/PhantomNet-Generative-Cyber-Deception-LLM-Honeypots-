FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the code only. The .env file (your API key) is NOT copied into the image.
COPY *.py ./
COPY pages ./pages
COPY start.sh ./
RUN sed -i 's/\r$//' start.sh

EXPOSE 5000 8501
CMD ["bash", "start.sh"]