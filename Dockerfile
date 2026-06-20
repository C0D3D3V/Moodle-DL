FROM python:3

# Bring in the uv binary (used to build and install the package).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ADD . /md

WORKDIR /md

RUN uv pip install --system .

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y ffmpeg

ENTRYPOINT ["moodle-dl", "--path", "/files"]
