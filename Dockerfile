FROM ubuntu:16.04 
RUN apt-get -y update \ 
    && apt-get -y install --no-install-recommends \
    build-essential \
    python3-dev \
    python3-pip \
    libffi-dev \
    libssl-dev \
    openssh-client \
    rsync \
    git \
    unzip
RUN pip3 install --upgrade pip setuptools \
    && ln -s pip3 /usr/bin/pip \
    && ln -sf /usr/bin/python3 /usr/bin/python
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
COPY webexteamssdk /webexteamssdk
RUN pip install /webexteamssdk
RUN pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
RUN pip install duckduckpy
RUN apt-get install libhunspell-dev -y
RUN pip install spacy
RUN pip install spacy_hunspell
RUN pip install dateparser
RUN pip install networkx
RUN pip install datefinder
RUN python -m spacy download en
ADD https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip /tmp/ngrok.zip
RUN set -x \
    && unzip -o /tmp/ngrok.zip -d /bin
WORKDIR workspace
ENTRYPOINT ["bash"]
