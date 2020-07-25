FROM python:3

ADD . /md

WORKDIR /md

RUN pip3 install -r requirements.txt

ENTRYPOINT ["python3", "main.py", "--path", "/files"]
