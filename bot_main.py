from config import *

import time as time_module

import telebot, os, pymongo, threading, time, logging, schedule, sched
from datetime import datetime, timedelta

from flask import Flask, request
from waitress import serve
from time import sleep
from threading import Thread
from random import randint

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

def schedule_checker():
    while True:
        schedule.run_pending()
        sleep(1)

isActivePoleCubata = False

global db
global client

global score

try:
    logger.info("Connecting to DB ATLAS")
    client = pymongo.MongoClient(
        "mongodb+srv://" + DB_USER + ":" + DB_PWD + "@" + DB_MONGO_HOST + "/?retryWrites=true&w=majority")
    db = client["UserData"]
    logger.info("Connected to DB ATLAS ")
except Exception as ex:
    logger.error("Error connecting to DB ATLAS: " + str(ex))

bot = telebot.TeleBot(TELEGRAM_TOKEN)
web_server = Flask(__name__)


@web_server.route('/', methods=['POST'])
def webhook():
    if request.headers.get("content-type") == "application/json":
        update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
        bot.process_new_updates([update])
        return "OK", 200


@bot.message_handler(content_types=["text"])
def process_txt_message(message):
    logger.info(message.text)
    if message.text.startswith('!'):
        process_internal_command(message)
    else:
        process_pole_event(message)


def process_internal_command(message):
    if message.text == '!polecubatainfo':
        show_info_message(message)
    elif message.text == '!polecubatarank':
        show_classical_pole_rank(message)
        
def process_pole_event(message):
    now = datetime.utcnow() + timedelta(days=1)
    year = now.year
    month = now.month
    day = now.day

    if datetime.datetime(year, month, day, 6, 0) < datetime.utcnow() and \
            datetime.utcnow() < datetime.datetime(year, month, day, 9, 15) and \
            isActivePoleCubata and message.text == 'Pole Cubata':
        logger.info("El borracho " + user_name + " ha hecho la pole Cubata")
        isActivePoleCubata = false
        add_score_to_user(message.chat.id, message.from_user.id)

def add_score_to_user(user_id, chat_id):
    try:
        global score

        collection = db["ranking-cubata-" + str(chat_id)]

        user = collection.find_one({"_id": user_id})

        if user:
            user['score'] += score;
            collection.find_one_and_update({"_id": user_id}, {"$set": user})
        else:
            collection.insert_one({"_id": user_id, "score": score})
    except Exception as ex:
        logger.error("Error saving score: " + str(ex))


def show_classical_pole_rank(message):
    try:
        collection = db["ranking-cubata-" + str(message.chat.id)]

        html_message = "\n&#129347 <b>POLE CUBATA RANK </b> &#129347 \n\n";
        for user in collection.find().sort("score", pymongo.DESCENDING):
            chat_member = bot.get_chat_member(message.chat.id, user['_id']).user

            html_message += "&#127864; " + chat_member.full_name + "  -->  " + str(user['score']) + " score \n"

        html_message += "\n&#129347;&#129347;&#129347;&#129347;&#129347;&#129347;&#129347;"

        bot.send_message(message.chat.id, html_message, parse_mode='HTML')
    except Exception as ex:
        logger.error("Error showing score: " + str(ex))


def show_info_message(message):
    bot.send_message(message.chat.id,
                     "\n&#127864;&#127864;&#127864;&#127864;&#127864;&#127864;&#127864;&#127864;&#127864; \n\n"
                     "¡¡Bienvenid@ a <b>Pole Cubata Bot</b>!! \n\n " \
                     "¡Te contarúaas laas nformnas pfero estoty bforrachisimo asi quete jds! \n" \
                     "&#129326;&#129326;&#129326;&#129326;&#129326; \n" \
                     "\n&#127864;&#127864;&#127864;&#127864;&#127864;&#127864;&#127864;&#127864;&#127864; \n\n",
                     parse_mode='HTML')


def polling():
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling()


def start_web_server():
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f'https://{APP}.herokuapp.com')
    serve(web_server, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


if __name__ == '__main__':

    Thread(target=schedule_checker).start()

    if os.environ.get("DYNO_RAM"):
        thread = threading.Thread(name="thread_web_server", target=start_web_server)
    else:
        thread = threading.Thread(name="thread_polling", target=polling)
    thread.start()
