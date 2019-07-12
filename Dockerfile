FROM ubuntu:18.04

WORKDIR /app

RUN apt-get update

RUN apt-get upgrade -y

RUN apt-get install python -y

RUN apt-get install software-properties-common -y

RUN apt-add-repository ppa:ansible/ansible

RUN apt-get update

RUN apt-get install ansible -y

RUN apt-get update

RUN apt install python-pip -y

COPY . /app

RUN pip install -r requirements.txt

ENTRYPOINT ["python"]

CMD ["final_extcred_exeplay.py"]
