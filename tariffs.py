from client import titlecase
import config
from work_with_db import Database
from telebot import types
from types import SimpleNamespace
from datetime import datetime

user_state = {}

db = Database()

EXIT = ['exit','/exit','quit','/quit']
YES = "yes"
NO = "no"
BK = "back"
SK = "skip"

def nospace(s):   return s.replace(" ", "")
def lower_ns(s):  return s.lower().replace(" ", "")
def titlecase(name):
    name = " ".join(name.split()).strip()
    def capitalize_part(part):
        return "-".join(p.capitalize() for p in part.split("-"))
    
    def capitalize_apostrophe(part):
        return "'".join(p.capitalize() for p in part.split("'"))
    words = []
    for word in name.split():
        word = capitalize_apostrophe(word)
        word = capitalize_part(word)     
        words.append(word)
    return " ".join(words)

def yes_no_answer(bot, message):
    if lower_ns(message.text) == YES:
        on_yes(bot,message)
    elif lower_ns(message.text) == NO:
        on_false(bot,message)
    else:
        bot.send_message(message.chat.id, "Please type 'yes' or 'no':", reply_markup=yes_no_markup())
        return bot.register_next_step_handler(message, lambda msg: yes_no_answer(bot, msg))

def on_yes(bot, message):
    match user_state.get(message.chat.id, {}).get("process"):
        case 'add_tariff':
            add_tariff_steps(bot, message)
        case 'remove_tariff':
            remove_tariff_steps(bot, message)
        case 'remove_tariff_type':
            if db.remove_tariff_type_from_db(user_state[message.chat.id]["data"]["name"]):
                bot.send_message(message.chat.id, f"Tariff type removed:\n\nName: {user_state[message.chat.id]['data']['name']}", reply_markup=rm_kb())
            else:
                bot.send_message(message.chat.id, "Error removing tariff type.", reply_markup=rm_kb())
            reset_state(message.chat.id)

def on_false(bot, message):
    bot.send_message(message.chat.id, "Operation cancelled.", reply_markup=rm_kb())
    reset_state(message.chat.id)

def yes_no_markup():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(YES, NO)
    return markup

def rm_kb():
    return types.ReplyKeyboardRemove()

def check_exit(bot, message):
    if lower_ns(message.text) in EXIT:
        bot.send_message(message.chat.id, "Operation cancelled.", reply_markup=rm_kb())
        reset_state(message.chat.id)
        return True
    return False

def is_valid_date(date_str: str, fmt: str = "%m-%Y") -> bool:
    date_str = nospace(date_str)
    try:
        datetime.strptime(date_str, fmt)
        return datetime.strptime(date_str, fmt)
    except ValueError:
        return False

def reset_state(chat_id):
    user_state[chat_id] = {"step": 0, "data": {},"process": '', "old_data": {}}

def back_btn(info = None):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(BK)
    return markup

def handle_back(bot, message, state, back_step):
    text = lower_ns(message.text)
    if text == BK:
        user_state[message.chat.id]["step"] =  state["step"] - back_step
        return "backing"
    return None

def back_skip(info = None):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    if info:
        markup.row(info)
    markup.row(BK, SK)
    return markup

# ADDING TARIFFS

def add_tariff(bot,message):
    reset_state(message.chat.id)
    bot.send_message(message.chat.id, "Enter tariffs's name:", reply_markup=rm_kb())
    bot.register_next_step_handler(message, lambda msg: add_tariff_steps(bot, msg))

def add_tariff_steps(bot, message):
    if check_exit(bot, message):
        return
    chat_id = message.chat.id
    state = user_state.get(chat_id)
    state ["process"] = 'add_tariff'
    step = state["step"]

    match step:
        case -1:
            return add_tariff(bot,message)
        case 0:
            name = titlecase(message.text)
            if len(name) > 50:
                bot.send_message(chat_id, "Too many characters entered. (max is 50)", reply_markup=back_btn())
                return bot.register_next_step_handler(message, lambda msg: add_tariff_steps(bot, msg))
            elif not db.check_tariff_type_exists(name):
                bot.send_message(chat_id, "This type of tariff is not exists. Please enter a different name.", reply_markup=back_btn())
                return bot.register_next_step_handler(message, lambda msg: add_tariff_steps(bot, msg))
            state["data"]["name"] = name
            bot.send_message(chat_id, f"Tariff's name: {name}\n\nEnter tariff's price:")
            state["step"] = 1
            bot.register_next_step_handler(message, lambda msg: add_tariff_steps(bot, msg))

        case 1:
            res = handle_back(bot, message, state, back_step=2)
            if res == "backing":
                return add_tariff_steps(bot, message)
            try:
                price = round(float(nospace(message.text)),2)
                if price < 0:
                    raise ValueError
            except ValueError:
                bot.send_message(chat_id, "Invalid price. Please enter a valid positive number.", reply_markup=back_btn())
                return bot.register_next_step_handler(message, lambda msg: add_tariff_steps(bot, msg))
            state["data"]["price"] = price
            bot.send_message(chat_id, f"Tariff's price: {price}\n\nEnter date from which tariff works", reply_markup=back_btn())
            state["step"] = 2
            bot.register_next_step_handler(message, lambda msg: add_tariff_steps(bot, msg))
        case 2:
            res = handle_back(bot, message, state, back_step=2)
            if res == "backing":
                new_msg = SimpleNamespace(**vars(message))
                new_msg.text = state['data']['name']
                return add_tariff_steps(bot, new_msg)
            elif not is_valid_date(message.text):
                bot.send_message(chat_id, "Invalid date format. Please enter the date in MM-YYYY format.", reply_markup=back_btn())
                return bot.register_next_step_handler(message, lambda msg: add_tariff_steps(bot, msg))
            state['data']['date_from'] = is_valid_date(message.text)
            state["step"] = 3
            bot.send_message(chat_id, f"Tariff's price: {state["data"]["price"]}\n\nEnter to which date tariff works\n"
                             "You can type \"skip\" ", reply_markup=back_skip())
            bot.register_next_step_handler(message, lambda msg: add_tariff_steps(bot, msg))
        case 3:
            res = handle_back(bot, message, state, back_step=2)
            if res == "backing":
                new_msg = SimpleNamespace(**vars(message))
                new_msg.text = str(state['data']['price'])
                return add_tariff_steps(bot, new_msg)
            elif not is_valid_date(message.text) and SK != lower_ns(message.text):
                bot.send_message(chat_id, "Invalid date format. Please enter the date in MM-YYYY format.", reply_markup=back_skip())
                return bot.register_next_step_handler(message, lambda msg: add_tariff_steps(bot, msg))
            state['data']['date_to'] = is_valid_date(message.text) if SK != lower_ns(message.text) else None
            state["step"] = 4
            bot.send_message(chat_id, f"Please confirm the addition of the following tariff:\n\nName: {state['data']['name']}"
                             f"\nPrice: {state['data']['price']}"
                             f"\nValid From: {state['data']['date_from'].strftime('%m-%Y')}\n"
                             f"Valid To: {state['data']['date_to'].strftime('%m-%Y') if state['data']['date_to'] else 'No end date'}"
                             f"\n\nType 'yes' to confirm or 'no' to cancel.", reply_markup=yes_no_markup())
            bot.register_next_step_handler(message, lambda msg: yes_no_answer(bot, msg))
        case 4:
            if db.add_tariff_in_db(state['data']['name'], state['data']['price'], state['data']['date_from'], state['data']['date_to']):
                bot.send_message(chat_id, f"Tariff added:\n\nName: {state['data']['name']}", reply_markup=rm_kb())
            else:
                bot.send_message(chat_id, "Error adding tariff.", reply_markup=rm_kb())
            reset_state(chat_id)

    # REMOVING TARIFFS

def remove_tariff(bot,message):
    reset_state(message.chat.id)
    bot.send_message(message.chat.id, "Enter tariffs's id:", reply_markup=rm_kb())
    bot.register_next_step_handler(message, lambda msg: remove_tariff_steps(bot, msg))

def remove_tariff_steps(bot, message):
    if check_exit(bot, message):
        return
    chat_id = message.chat.id
    state = user_state.get(chat_id)
    state ["process"] = 'remove_tariff'
    step = state["step"]
    match step:
        case -1:
            return remove_tariff(bot,message)
        case 0:
            try:
                tariff_id = int(nospace(message.text))
                if tariff_id < 1:
                    raise ValueError
            except ValueError:
                bot.send_message(chat_id, "Invalid id. Please enter a valid positive integer.", reply_markup=back_btn())
                return bot.register_next_step_handler(message, lambda msg: remove_tariff_steps(bot, msg))
            if not db.check_tariff_exists(tariff_id):
                bot.send_message(chat_id, "This tariff is not exists. Please enter a different id.", reply_markup=back_btn())
                return bot.register_next_step_handler(message, lambda msg: remove_tariff_steps(bot, msg))
            state["data"]["id"] = tariff_id
            tariff = db.show_tariff_in_db(tariff_id)
            bot.send_message(chat_id, f"Are you sure, you want to remove:\n{tariff}", reply_markup=yes_no_markup())
            state["step"] = 1
            bot.register_next_step_handler(message, lambda msg: yes_no_answer(bot, msg))
        case 1:
            if db.remove_tariff_from_db(state['data']['id']):
                bot.send_message(chat_id, f"Tariff removed:\n\nId: {state['data']['id']}", reply_markup=rm_kb())
            else:
                bot.send_message(chat_id, "Error removing tariff.", reply_markup=rm_kb())
            reset_state(chat_id)

    # ADDING TYPES

def add_tariff_type(bot,message):
    reset_state(message.chat.id)
    bot.send_message(message.chat.id, "Enter new tariff type's name:", reply_markup=rm_kb())
    bot.register_next_step_handler(message, lambda msg: add_tariff_type_steps(bot, msg))

def add_tariff_type_steps(bot, message):
    if check_exit(bot, message):
        return
    chat_id = message.chat.id
    name = titlecase(message.text)
    if len(name) > 50:
        bot.send_message(chat_id, "Too many characters entered. (max is 50)", reply_markup=back_btn())
        return bot.register_next_step_handler(message, lambda msg: add_tariff_type_steps(bot, msg))
    elif db.check_tariff_type_exists(name):
        bot.send_message(chat_id, "This type of tariff already exists. Please enter a different name.", reply_markup=back_btn())
        return bot.register_next_step_handler(message, lambda msg: add_tariff_type_steps(bot, msg))
    if db.add_tariff_type_in_db(name):
        bot.send_message(chat_id, f"Tariff type added:\n\nName: {name}", reply_markup=rm_kb())
    else:
        bot.send_message(chat_id, "Error adding tariff type.", reply_markup=rm_kb())
    
    # REMOVING TYPES

def remove_tariff_type(bot,message):
    reset_state(message.chat.id)
    bot.send_message(message.chat.id, "Enter tariff type's name to remove:", reply_markup=rm_kb())
    bot.register_next_step_handler(message, lambda msg: remove_tariff_type_steps(bot, msg))

def remove_tariff_type_steps(bot, message):
    if check_exit(bot, message):
        return
    chat_id = message.chat.id
    name = titlecase(message.text)
    if len(name) > 50:
        bot.send_message(chat_id, "Too many characters entered. (max is 50)", reply_markup=back_btn())
        return bot.register_next_step_handler(message, lambda msg: remove_tariff_type_steps(bot, msg))
    elif not db.check_tariff_type_exists(name):
        bot.send_message(chat_id, "This type of tariff does not exist. Please enter a different name.", reply_markup=back_btn())
        return bot.register_next_step_handler(message, lambda msg: remove_tariff_type_steps(bot, msg))
    elif db.check_associated_tariffs(name):
        bot.send_message(chat_id, "This type of tariff has associated tariffs. Please remove them first.", reply_markup=back_btn())
        return on_false(bot, message)
    bot.send_message(chat_id, f"Are you sure, you want to remove all tariffs of type:\n{name}", reply_markup=yes_no_markup())
    user_state[chat_id] = {"data": {"name": name}, "process": 'remove_tariff_type'}
    bot.register_next_step_handler(message, lambda msg: yes_no_answer(bot, msg))

