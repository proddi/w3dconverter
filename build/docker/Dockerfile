FROM ubuntu:xenial
MAINTAINER Proddi <proddi@splatterladder.com>

RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y gcc python3-dev python3-venv python3-pil && \
    apt-get autoclean -y

# i don't know why ubuntu doesn't populate dist-packages by default
ENV PYTHONPATH=/usr/lib/python3/dist-packages

# http://askubuntu.com/questions/15926/how-to-avoid-duplicate-entries-in-bash-history
RUN echo "export HISTCONTROL=ignoreboth:erasedups" >> ~/.bashrc

# install python environment
ADD requirements.txt /tmp/
RUN pyvenv /opt/py3_env && \
    /opt/py3_env/bin/pip install -r /tmp/requirements.txt && \
    rm -f /tmp/requirements.txt
