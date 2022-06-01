import telebot
import requests
import os
import threading
import shutil
import math
import speech_recognition as sr 
from pydub import AudioSegment
from pydub.silence import split_on_silence

TOKEN = bot = telebot.TeleBot(os.environ.get("TOKEN", ""))
bot = telebot.TeleBot(TOKEN)
r = sr.Recognizer()
global emode
emode = False

def get_large_audio_transcription(path,message):
    id = message.message_id
    sound = AudioSegment.from_wav(path)  
    chunks = split_on_silence(sound,
        min_silence_len = 500,
        silence_thresh = sound.dBFS-14,
        keep_silence=500,
    )

    folder_name = f"audio-chunks-{id}"
    if not os.path.isdir(folder_name):
        os.mkdir(folder_name)
    whole_text = ""

    tsize = os.path. getsize(path)
    edi = bot.send_message(message.chat.id,f"Total Size: {tsize}")
    psize = 0

    for i, audio_chunk in enumerate(chunks, start=1):
        chunk_filename = os.path.join(folder_name, f"chunk{i}.wav")
        audio_chunk.export(chunk_filename, format="wav")

        with sr.AudioFile(chunk_filename) as source:
            audio_listened = r.record(source)

            try:
                text = r.recognize_google(audio_listened)
            except sr.UnknownValueError as e:
                #print("Error:", str(e))
                whole_text += "\nError:\n"
            else:
                text = f"{text.capitalize()}. "
                #print(chunk_filename, ":", text)
                whole_text += text
        size = os.path. getsize(chunk_filename)        
        psize = psize + size
        bot.edit_message_text(f"Processed {psize/1024/1024} MB out of {tsize/1024/1024} MB - {math.floor(psize*100/tsize)}%",message.chat.id,edi.message_id)

    return whole_text


'''with sr.Microphone() as source:
    # read the audio data from the default microphone
    audio_data = r.record(source, duration=5)
    print("Recognizing...")
    # convert speech to text
    text = r.recognize_google(audio_data)
    print(text)
    
text = r.recognize_google(audio_data, language="es-ES")'''    


def splitfn(name,message):
    path = f"./{name}"
    converted = get_large_audio_transcription(path,message)

    try:
        bot.edit_message_text("Finished...Uploading",message.chat.id,message_id=message.message_id+1) 
    except:
        bot.send_message(message.chat.id,"Finished...Uploading")

    with open(f"Transcript-{message.message_id}.txt","w") as file:
        file.write(converted)

    doc = open(f"Transcript-{message.message_id}.txt", 'rb')
    bot.send_document(message.chat.id, doc)
    os.remove(f"Transcript-{message.message_id}.txt")
    os.remove(name)
    shutil.rmtree(f"audio-chunks-{message.message_id}", ignore_errors=True)

@bot.message_handler(commands=['start'])
def handle_welcome(message):
    bot.send_message(message.chat.id,"Welcome\nYou just have to send me a .wav file\nYou can convert to .wav in https://cloudconvert.com/mp3-to-wav")


@bot.message_handler(content_types=['document'])
def handle_documnet(message):
    name = message.document.file_name
    if ".wav" in name:
        id = message.document.file_id
        fsize = message.document.file_size
        try:#if(fsize<52428800):
            file_info = bot.get_file(id)
            bot.send_message(message.chat.id,"Downloading")
            file = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(TOKEN, file_info.file_path))
            with open(name,"wb") as stt:
                stt.write(file.content)
        except:#else:
            bot.send_message(message.chat.id,"File is too big to Download from Telegram Api, use /link command")  
            return      
        
        try:
            bot.edit_message_text("Converting",message.chat.id,message_id=message.message_id+1) 
        except:
            bot.send_message(message.chat.id,"Converting")

        sttc = threading.Thread(target=lambda:splitfn(name,message),daemon=True)
        sttc.start()  

    else:
        try:
            id = message.document.file_id
            file_info = bot.get_file(id)
            file = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(TOKEN, file_info.file_path))
            string = file.content
            n = 4096
            split = [string[i:i+n] for i in range(0, len(string), n)]
            for ele in split:
                bot.send_message(message.chat.id,ele)     
        except:#else:
            bot.send_message(message.chat.id,"File type not Supported")      
            
        
@bot.message_handler(commands=['link'])
def handle_link(message):
    try:
        link = message.text.split("link ")[1]
    except:
        bot.send_message(message.chat.id,"send link along with command")
        return

    bot.send_message(message.chat.id,"Downloading")
    sf = requests.get(link)

    with open(f"{message.message_id}.wav","wb") as stt:
            stt.write(sf.content)
    try:
        bot.edit_message_text("Converting",message.chat.id,message_id=message.message_id+1) 
    except:
            bot.send_message(message.chat.id,"Converting")

    sttc = threading.Thread(target=lambda:splitfn(f"{message.message_id}.wav",message),daemon=True)
    sttc.start()

@bot.message_handler(commands=['makefile'])
def handle_make(message):
    global emode
    bot.send_message(message.chat.id,"File Make Mode Enabled, \nSend text to make a file, \nFirst line is taken as File Name, \n/cancel to cancel the progress")
    emode = True

@bot.message_handler(commands=['cancel'])
def handle_make(message):
    global emode
    emode = False
    bot.send_message(message.chat.id, "Canceld")

@bot.message_handler(content_types=['text'])
def handle_documnet(message):
    global emode
    if emode == True:
        text = message.text.split("\n")
        firstline = text[0]
        text.remove(text[0])

        message.text = "" 
        for ele in text: 
            message.text = message.text + f"{ele}\n"  

        with open(firstline,"w") as file:
            file.write(message.text)  

        doc = open(firstline, 'rb')
        bot.send_document(message.chat.id, doc)
        os.remove(firstline)
        emode =  False



bot.polling(none_stop=True, timeout=123)            
