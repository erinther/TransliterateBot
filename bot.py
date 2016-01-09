import logging
import telebot
from telebot import types
from pymongo import MongoClient
from subprocess import (PIPE, Popen)

about_txt = """\
Hi there, I am TransliterateBot.
I am an unofficial bot which uses behnevis to transliterate finglish to Farsi.
Good news is, I am released under GPLv3 at github.com/Separius/TransliterateBot.
oh and I support inline !
"""

help_txt = """\
/about => about me
/help => this message
/suggest finglish persian => add your suggestion to the queue
/dict word replacement => always replaces 'word' with 'replacement'
/bug desc => bug report
/feature desc => feature request
/pref => set preferences
/* => transliterates the input
"""

nahal_dict = {"@":"at", "&":"and", "A":"ey", "B":"bi", "C":"si", "D":"di", "E":"ee", "F":"ef", "G":"ji", "H":"eh", "I":"aay", "J":"jey", "K":"key", "L":"el", "M":"em", "N":"en", "O":"o", "P":"pi", "Q":"kiu", "R":"aar", "S":"es", "T":"ti", "U":"yu", "V":"vi", "X":"iks", "Y":"vay", "Z":"zi"}

logging.basicConfig(format='%(asctime)s:%(funcName)s:%(message)s', filename='bot.log', level=logging.CRITICAL)

bot = telebot.TeleBot("<your bot token>")

client = MongoClient('mongodb://admin:password@ip:27017/')
db = client.bot


def is_user(chat):
    return chat.id > 0


def denahalize(text):
    for i in range(len(text)):
        for key, value in nahal_dict.items():
            #text = text.replace(key, value) #TODO
            break
    return text


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, about_txt+"\nfor more info check /help and please set your /pref")
    db["user_prefs"].update({'user_id': message.from_user.id}, {'$setOnInsert': {'user_id': message.from_user.id, "denahal": False, "filter": True, "parsi": False}}, upsert = True)


@bot.message_handler(commands=['help'])
def help(message):
    bot.reply_to(message, help_txt)


@bot.message_handler(commands=['about'])
def about(message):
    bot.reply_to(message, about_txt)


@bot.message_handler(commands=['suggest'])
def suggest(message):
    words = message.text.split()
    if(len(words) < 3):
        bot.reply_to(message, "give me 2 words")
        return
    if(db["suggestions"].find({'word': words[1]}).count()):
        db["suggestions"].update({'word': words[1]}, {"$inc": {"suggests."+' '.join(words[2:]): 1}})
    else:
        db["suggestions"].insert({'word': words[1], "suggests": {' '.join(words[2:]): 1}})
    bot.reply_to(message, "thanks for your suggestion")


@bot.message_handler(commands=['bug'])
def bug(message):
    logging.critical(str(message.from_user.id)+" : "+message.text)
    bot.reply_to(message, "Thanks!")


@bot.message_handler(commands=['feature'])
def feature(message):
    logging.critical(str(message.from_user.id)+" : "+message.text)
    bot.reply_to(message, "Thanks!")


@bot.message_handler(commands=['dict'])
def dict(message):
    words = message.text.split()
    if(len(words) < 3):
        bot.reply_to(message, "give me 2 words")
        return
    if(db["user_dicts"].find({'user_id': message.from_user.id}).count()):
        db["user_dicts"].update({'user_id': message.from_user.id}, {"$set": {"words."+words[1]: ' '.join(words[2:])}})
    else:
        db["user_dicts"].insert({'user_id': message.from_user.id, "words": {words[1]: ' '.join(words[2:])}})
    bot.reply_to(message, "added to your dictionary")


@bot.message_handler(commands=['pref'])
def pref(message):
    if(is_user(message.chat) == False):
        return
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add('enable', 'disable')
    msg = bot.send_message(chat_id, "Enable denahalization: ", reply_markup=markup)
    bot.register_next_step_handler(msg, pref_nahal)


def pref_nahal(message):
    user_id = message.from_user.id
    nahal = True if message.text == "enable" else False
    db["user_prefs"].update({'user_id': user_id}, {"$set": {"denahal": nahal}})
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add('enable', 'disable')
    msg = bot.send_message(chat_id, "Enable filtering: ", reply_markup=markup)
    bot.register_next_step_handler(msg, pref_filter)


def pref_filter(message):
    user_id = message.from_user.id
    filtering = True if message.text == "enable" else False
    db["user_prefs"].update({'user_id': user_id}, {"$set": {"filter": filtering}})
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add('enable', 'disable')
    msg = bot.send_message(chat_id, "Enable parsi saaz: ", reply_markup=markup)
    bot.register_next_step_handler(msg, pref_parsi)


def pref_parsi(message):
    user_id = message.from_user.id
    parsi = True if message.text == "enable" else False
    db["user_prefs"].update({'user_id': user_id}, {"$set": {"parsi": parsi}})
    chat_id = message.chat.id
    markup = types.ReplyKeyboardHide(selective=False)
    bot.send_message(chat_id, "all done", reply_markup=markup)


def use_dict(text, dic):
    for i in range(len(text)):
        for key, value in dic.items():
            if(text[i] == key):
                text[i] = value
                break
    return text


# TODO do the php job
def global_replaces(text):
    if db["replacement"].count():
        for i in range(len(text)):
            for key, value in db["replacements"].find().items():
                if(text[i] == key):
                    text[i] = value
                    break
    return text


# TODO
def filter_text(text):
    return text


# TODO
def parsi_text(text):
    return text

@bot.message_handler(content_types=['text'])
def transliterate(message):
    text = message.text
    if((text == "enable" or text == "disable")) and (is_user(message.chat) == True):
        return
    user_id = message.from_user.id
    logging.critical(str(user_id)+" : "+text)
    if text:
        if (text[0] == '/'):
            text = text[1:]
        text = text.replace("@TransliterateBot", "")
        text = text.split()
        user_dictionary = db["user_dicts"].find_one({"user_id": user_id})
        if(user_dictionary is not None):
            text = use_dict(text,user_dictionary["words"])
        pref = db["user_prefs"].find_one({'user_id': user_id})
        if(pref is None):
            db["user_prefs"].update({'user_id': message.from_user.id}, {'$setOnInsert': {'user_id': message.from_user.id, "denahal": False, "filter": True, "parsi": False}}, upsert = True)
            pref = db["user_prefs"].find_one({'user_id': user_id})
        if(pref["denahal"]):
            text = denahalize(text)
        if(pref["filter"]):
            text = filter_text(text)
        if(pref["parsi"]):
            text = parsi_text(text)
        text = global_replaces(text)
        shcommand = ['php', './behnevis.php']
        shcommand.extend(text)
        p = Popen(shcommand, stdout=PIPE, stderr=PIPE)
        text, err = p.communicate()
        bot.reply_to(message, text)


@bot.message_handler(func=lambda message: True)
def drop(message):
    bot.reply_to(message, "Send me a text message")

@bot.inline_handler(lambda query: True)
def query_text(inline_query):
    try:
        text = inline_query.query
        print("input is "+text)
        user_id = inline_query.from_user.id
        logging.critical(str(user_id)+" : "+text)
        text = text.split()
        user_dictionary = db["user_dicts"].find_one({"user_id": user_id})
        if(user_dictionary is not None):
            text = use_dict(text,user_dictionary["words"])
        pref = db["user_prefs"].find_one({'user_id': user_id})
        if(pref is None):
            db["user_prefs"].update({'user_id': inline_query.from_user.id}, {'$setOnInsert': {'user_id': inline_query.from_user.id, "denahal": False, "filter": True, "parsi": False}}, upsert = True)
            pref = db["user_prefs"].find_one({'user_id': user_id})
        if(pref["denahal"]):
            text = denahalize(text)
        if(pref["filter"]):
            text = filter_text(text)
        if(pref["parsi"]):
            text = parsi_text(text)
        text = global_replaces(text)
        shcommand = ['php', './behnevis.php']
        shcommand.extend(text)
        p = Popen(shcommand, stdout=PIPE, stderr=PIPE)
        text, err = p.communicate()
        text = text.decode("utf-8")
        print("sending: "+text)
        r = types.InlineQueryResultArticle('1', text, text)
        bot.answer_inline_query(inline_query.id, [r])
    except Exception as e:
        print(e)

bot.polling()
