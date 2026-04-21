FROM python:3.11-slim

RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*

WORKDIR /judge
COPY . /judge

RUN pip install -r requirements.txt

RUN mkdir -p /judge/assets && python3 /judge/gen_image.py

EXPOSE 8080

CMD ["python", "server.py"]
