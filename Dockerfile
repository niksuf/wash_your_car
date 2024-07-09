FROM python:3.12

RUN mkdir /wash_your_car
COPY . /wash_your_car
WORKDIR /wash_your_car

RUN adduser --quiet --disabled-password --shell /bin/bash --home /home/wash_your_car wash_your_car
RUN echo "wash_your_car ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
USER wash_your_car

RUN pip install --upgrade --no-warn-script-location pip
RUN pip install --user --no-warn-script-location -r requirements.txt

CMD python -u scripts/main.py
