FROM python:3

ADD . /md

WORKDIR /md

RUN pip3 install .

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y ffmpeg

ENTRYPOINT ["moodle-dl", "--path", "/files"]
