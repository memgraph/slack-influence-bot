FROM python:3.9

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
    apt-get --yes install cmake

WORKDIR /app
COPY . .
RUN python3 -m pip install -r requirements.txt

CMD ["python3", "slack_stream.py"]
