FROM anasty17/mltb:latest

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

COPY requirements.txt .
COPY update.py .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD python3 update.py && python3 -m bot
