import json
import telebot
import requests
from telebot import types

about_txt = """\
Hi there, I am TransliterateBot.
I am an unofficial bot which uses behnevis to transliterate finglish to Farsi.
Good news is, I am released under GPLv3 at github.com/Separius/TransliterateBot.
oh and I support inline !
"""

help_txt = """\
/about => about me
/help => this message
/* => transliterates the input
"""

headers = {
    'Referer': 'https://behnevis.com/',
    'Origin': 'https://behnevis.com',
    'Save-Data': 'on',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
    'DNT': '1',
    'Content-Type': 'text/plain',
}

behnevis_url = 'https://9mkhzfaym3.execute-api.us-east-1.amazonaws.com/production/convert'

bot = telebot.TeleBot("<your token here>")


def is_user(chat):
    return chat.id > 0


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, about_txt+"\nfor more info check /help")


@bot.message_handler(commands=['help'])
def help(message):
    bot.reply_to(message, help_txt)

def _transliterate(text):
    response = requests.post(behnevis_url, headers=headers, data=text).text
    response = json.loads(response)
    return ' '.join([response[k] for k in text.split()])

@bot.message_handler(commands=['about'])
def about(message):
    bot.reply_to(message, about_txt)


@bot.message_handler(content_types=['text'])
def transliterate(message):
    text = message.text
    if((text == "enable" or text == "disable")) and (is_user(message.chat) == True):
        return
    user_id = message.from_user.id
    if text:
        if (text[0] == '/'):
            text = text[1:]
        text = text.replace("@TransliterateBot", "")
        bot.reply_to(message, _transliterate(text))


@bot.message_handler(func=lambda message: True)
def drop(message):
    bot.reply_to(message, "Send me a text message")

@bot.inline_handler(lambda query: True)
def query_text(inline_query):
    try:
        text = inline_query.query
        user_id = inline_query.from_user.id
        text = _transliterate(text)
        r = types.InlineQueryResultArticle('1', text, types.InputTextMessageContent(text))
        bot.answer_inline_query(inline_query.id, [r])
    except Exception as e:
        print(e)

bot.polling()
