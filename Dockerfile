FROM python:3

ADD . /md

WORKDIR /md

RUN pip3 install .

ENTRYPOINT ["moodle-dl", "--path", "/files"]
