import telebot
from config import TOKEN, logger
from work_with_db import Database
from client import (add_client, remove_client, edit_client, show_client)
from tariffs import add_tariff, remove_tariff, add_tariff_type, remove_tariff_type
from telebot import types

bot = telebot.TeleBot(TOKEN)

logger.info("Bot started")

db = Database()

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "clients")
    bot.send_message(message.chat.id, db.show_all_clients())
    bot.send_message(message.chat.id, "tariff types")
    bot.send_message(message.chat.id, db.show_all_tariff_types())
    bot.send_message(message.chat.id, "tariffs")
    bot.send_message(message.chat.id, db.show_all_tariffs())
    

@bot.message_handler(commands=["add_client","client_add",'add'])
def call_add_client(message):
    add_client(bot, message)

@bot.message_handler(commands=["remove_client","client_remove",'remove'])
def call_remove_client(message):
    remove_client(bot, message)

@bot.message_handler(commands=["edit_client","client_edit",'edit'])
def call_edit_client(message):
    edit_client(bot, message)

@bot.message_handler(commands=["show_client","client_show"])
def call_edit_client(message):
    show_client(bot, message)

@bot.message_handler(commands=["add_tariff","tariff_add"])
def call_add_tariff(message):
    add_tariff(bot, message)

@bot.message_handler(commands=["remove_tariff","tariff_remove"])
def call_romove_tariff(message):
    remove_tariff(bot, message)

@bot.message_handler(commands=["add_tariff_type","tariff_type_add","add_type","type_add"])
def call_add_tariff_type(message):
    add_tariff_type(bot, message)

@bot.message_handler(commands=["remove_tariff_type","tariff_type_remove","type_remove","remove_type"])
def call_romove_tariff_type(message):
    remove_tariff_type(bot, message)

@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.reply_to(message, message.text)


bot.infinity_polling()