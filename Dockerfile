FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
