FROM python:3.9

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

# Install cmake to build pymgclient (used in gqlalchemy)
RUN apt-get update && \
    apt-get --yes install cmake

# Install poetry
RUN pip install -U pip \
    && curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
ENV PATH="${PATH}:/root/.poetry/bin"

WORKDIR /app
COPY . .
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

ENTRYPOINT [ "poetry", "run" ]
CMD ["python3", "-m", "main"]
