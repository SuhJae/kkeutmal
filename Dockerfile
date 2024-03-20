FROM python:3.12

WORKDIR /bot

ENV PYTHONPATH=/

COPY ./requirements.txt /bot/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /bot/requirements.txt

COPY ./bot /bot

CMD ["python", "main.py"]
