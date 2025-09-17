from http import client
import config
from work_with_db import Database
from telebot import types
from types import SimpleNamespace
import re

user_state = {}

db = Database()

STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"
EXIT = ['exit','/exit','quit','/quit']
YES = "yes"
NO = "no"
BK = "back"
SK = "skip"

def check_exit(bot, message):
    if lower_ns(message.text) in EXIT:
        bot.send_message(message.chat.id, "Operation cancelled.", reply_markup=rm_kb())
        reset_state(message.chat.id)
        return True
    return False

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

def is_name(s):
    allowed = {"-", "'"}
    return all(ch.isalpha() or ch.isspace() or ch in allowed for ch in s)

def is_phone(number):
    number = nospace(number)
    if not number:
        return False
    if number.startswith("+"):
        return number[1:].isdigit()
    return number.isdigit()

def rm_kb():
    return types.ReplyKeyboardRemove()

def back_skip(info = None):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    if info:
        if info == "status":
            markup.row(STATUS_ACTIVE, STATUS_INACTIVE)
        else:
            markup.row(info)
    markup.row(BK, SK)
    return markup

def back_btn(info = None):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    if info == "status":
            markup.row(STATUS_ACTIVE, STATUS_INACTIVE)
    markup.row(BK)
    return markup

def handle_back(bot, message, state, back_step):
    text = lower_ns(message.text)
    if text == BK:
        user_state[message.chat.id]["step"] =  state["step"] - back_step
        return "backing"
    return None

def reset_state(chat_id):
    user_state[chat_id] = {"step": 0, "data": {},"process": '', "old_data": {}}

def yes_no_markup():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(YES, NO)
    return markup

def yes_no_answer(bot, message):
    if lower_ns(message.text) == YES:
        on_yes(bot,message)
    elif lower_ns(message.text) == NO:
        on_false(bot,message)
    else:
        bot.send_message(message.chat.id, "Please type 'yes' or 'no':", reply_markup=yes_no_markup())
        return bot.register_next_step_handler(message, lambda msg: yes_no_answer(bot, msg))

def on_yes(bot, message):
    match user_state[message.chat.id]["process"]:
        case 'add_client':
            match user_state[message.chat.id]["step"]:
                case 0:
                    user_state[message.chat.id]["step"] = 1
                    user_state[message.chat.id]["old_data"] = db.get_client(user_state[message.chat.id]["data"]["client_number"])
                    edit_client_steps(bot,message)
        case 'remove_client':
            user_state[message.chat.id]["step"] = 1
            remove_client_steps(bot,message)
        case 'edit_client':
            match user_state[message.chat.id]["step"]:
                case 0:
                    add_client_steps(bot,message)
                case 1:
                    edit_client_steps(bot,message)
                case 6:
                    user_state[message.chat.id]["step"] = 7
                    edit_client_steps(bot,message)

def on_false(bot, message):
    bot.send_message(message.chat.id, "Operation cancelled.", reply_markup=rm_kb())
    reset_state(message.chat.id)

def show_client(bot,message):
    bot.send_message(message.chat.id, "Enter client's number to show:", reply_markup=rm_kb())
    bot.register_next_step_handler(message, lambda msg: show_client_by_number(bot, msg))

def show_client_by_number(bot,message):
    if check_exit(bot, message):
        return
    chat_id = message.chat.id
    client_number = nospace(message.text)
    if db.check_client_exists(client_number):
        client = db.show_client_in_db(client_number)
        bot.send_message(chat_id, f"Client details:\n {client}", reply_markup=rm_kb())
    else:
        bot.send_message(chat_id, "Client with this number does not exist.", reply_markup=rm_kb())

        # ADD CLIENT

def add_client(bot,message):
    reset_state(message.chat.id)
    bot.send_message(message.chat.id, "Enter client's number:", reply_markup=rm_kb())
    bot.register_next_step_handler(message, lambda msg: add_client_steps(bot, msg))

def add_client_steps(bot, message):
    if check_exit(bot, message):
        return
    chat_id = message.chat.id
    state = user_state.get(chat_id)
    state ["process"] = 'add_client'
    step = state["step"]

    match step:

        case -1:
            return add_client(bot,message)

        case 0:
            res = handle_back(bot, message, state, back_step=1)
            if res == "backing":
                return add_client_steps(bot, message)
            if 'client_number' not in state['data']:
                if len(nospace(message.text)) > 20:
                    bot.send_message(chat_id, "Too many characters entered. (max is 20)", reply_markup=back_btn())
                    return bot.register_next_step_handler(message, lambda msg: add_client_steps(bot, msg))
                state["data"]["client_number"] = nospace(message.text)

            if db.check_client_exists(state["data"]["client_number"]):
                bot.send_message(chat_id, "Client with this number already exists. Do you want to edit it?", reply_markup=yes_no_markup())
                bot.register_next_step_handler(message, lambda msg: yes_no_answer(bot, msg))
            else:
                state["step"] = 1
                bot.send_message(chat_id, "Enter client's name:", reply_markup=back_btn())
                bot.register_next_step_handler(message, lambda msg: add_client_steps(bot, msg))

        case 1:
            res = handle_back(bot, message, state, back_step=2)
            if res == "backing":
                return add_client_steps(bot, message)
            elif  not is_name(titlecase(message.text)):
                bot.send_message(chat_id, "Please enter a valid name (letters, spaces, hyphens, apostrophes only):", reply_markup=back_btn())
                return bot.register_next_step_handler(message, lambda msg: add_client_steps(bot, msg))
            elif len(titlecase(message.text)) > 70:
                bot.send_message(chat_id, "Too many characters entered. (max is 70)", reply_markup=back_btn())
                return bot.register_next_step_handler(message, lambda msg: add_client_steps(bot, msg))
            state["data"]["name"] = titlecase(message.text)
            state["step"] = 2
            bot.send_message(chat_id, "Enter client's surname:", reply_markup=back_btn())
            bot.register_next_step_handler(message, lambda msg: add_client_steps(bot, msg))

        case 2:
            res = handle_back(bot, message, state, back_step=2)
            if res == "backing":
                new_msg = SimpleNamespace(**vars(message))
                new_msg.text = state['data']['client_number']
                return add_client_steps(bot, new_msg)
            elif  not is_name(titlecase(message.text)):
                bot.send_message(chat_id, "Please enter a valid surname (letters, spaces, hyphens, apostrophes only):", reply_markup=back_btn())
                return bot.register_next_step_handler(message, lambda msg: add_client_steps(bot, msg))
            elif len(titlecase(message.text)) > 70:
                bot.send_message(chat_id, "Too many characters entered. (max is 70)", reply_markup=back_btn())
                return bot.register_next_step_handler(message, lambda msg: add_client_steps(bot, msg))
            state["data"]["surname"] = titlecase(message.text) 
            state["step"] = 3
            bot.send_message(chat_id, "Enter client's phone number:", reply_markup=back_skip())
            bot.register_next_step_handler(message, lambda msg: add_client_steps(bot, msg))

        case 3:
            res = handle_back(bot, message, state, back_step=2)
            if res == "backing":
                new_msg = SimpleNamespace(**vars(message))
                new_msg.text = state['data']['name']
                return add_client_steps(bot, new_msg)
            elif lower_ns(message.text) != SK:
                if not is_phone(message.text):
                    bot.send_message(chat_id,"Please enter a valid phone number", reply_markup=back_skip())
                    return bot.register_next_step_handler(message, lambda msg: add_client_steps(bot, msg))
                elif db.check_phone_exists(nospace(message.text)):
                    bot.send_message(chat_id, "This phone number is already associated with another client."
                                    "Please enter a different phone number or type 'skip':", reply_markup=back_skip())
                    return bot.register_next_step_handler(message, lambda msg: add_client_steps(bot, msg))
            elif len(nospace(message.text)) > 20:
                bot.send_message(chat_id, "Too many characters entered. (max is 20)", reply_markup=back_btn())
                return bot.register_next_step_handler(message, lambda msg: add_client_steps(bot, msg))
            state['data']['phone_number'] = None if lower_ns(message.text) == SK  else nospace(message.text)
            bot.send_message(chat_id, "Enter client's status (active/inactive):", reply_markup=back_btn("status"))
            bot.register_next_step_handler(message, lambda msg: add_client_steps(bot, msg))
            state["step"] = 4

        case 4:
            res = handle_back(bot, message, state, back_step=2)
            if res == "backing":
                new_msg = SimpleNamespace(**vars(message))
                new_msg.text = state['data']['surname']
                return add_client_steps(bot, new_msg)
            if lower_ns(message.text) in [STATUS_ACTIVE, STATUS_INACTIVE]:
                state["data"]["status"] = lower_ns(message.text)
            else:
                state["data"]["status"] = STATUS_ACTIVE
            if db.add_client_in_db(state["data"]["client_number"],
                              state["data"]["name"],
                              state["data"]["surname"],
                              state["data"]["status"],
                              state["data"]["phone_number"]):
                client = db.show_client_in_db(state["data"]["client_number"])
                bot.send_message(chat_id, f"✅ Client:\n {client} \n successfully added!", reply_markup=rm_kb())
            else:
                bot.send_message(chat_id, "Failed to add client.", reply_markup=rm_kb())
            reset_state(chat_id)

    # REMOVE CLIENT

def remove_client(bot,message):
    reset_state(message.chat.id)
    bot.send_message(message.chat.id, "Enter client's number to remove:", reply_markup=rm_kb())
    bot.register_next_step_handler(message, lambda msg: remove_client_steps(bot, msg))

def remove_client_steps(bot, message):
    if check_exit(bot, message):
        return
    chat_id = message.chat.id
    state = user_state.get(chat_id)
    state["process"] = 'remove_client'
    step = state["step"]
    if step == 0:
        if not state:  
            return bot.send_message(chat_id, "Something get wrong, type /remove_client once more")
        if db.check_client_exists(nospace(message.text)):
            state["data"]["client_number"] = nospace(message.text)
            client = db.show_client_in_db(nospace(message.text))
            bot.send_message(chat_id, f"Are you sure you want to remove:\n {client} ?", reply_markup=yes_no_markup())
            bot.register_next_step_handler(message, lambda msg: yes_no_answer(bot, msg))
        else:
            bot.send_message(chat_id, "Client with this number does not exist. Operation cancelled.", reply_markup=rm_kb())
            reset_state(chat_id)
    elif step == 1:
        client = db.show_client_in_db(state["data"]["client_number"])
        if db.remove_client_from_db(state["data"]["client_number"]):
            bot.send_message(chat_id, f"✅ Client:\n {client} \n successfully removed!", reply_markup=rm_kb())
        else:
            bot.send_message(chat_id, "Failed to remove client.", reply_markup=rm_kb())
        reset_state(chat_id)

    # EDIT CLIENT

def edit_client(bot,message):
    reset_state(message.chat.id)
    bot.send_message(message.chat.id, "Enter client's number to edit:", reply_markup=rm_kb())
    bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))

def edit_client_steps(bot, message):
    if check_exit(bot, message):
        return
    chat_id = message.chat.id
    state = user_state.get(chat_id)
    state ["process"] = 'edit_client'
    step = state["step"]
    curstep = step
    match step:

        case -1:
            return edit_client(bot,message)

        case 0:
            client_number = nospace(message.text)
            if db.check_client_exists(client_number):
                user_state[chat_id]["old_data"] = db.get_client(client_number)
                bot.send_message(chat_id, f"Do you Want to edit {db.show_client_in_db(user_state[chat_id]["old_data"][1])} ?", reply_markup=yes_no_markup())
                state["step"] = 1
                bot.register_next_step_handler(message, lambda msg: yes_no_answer(bot, msg))
            else:
                bot.send_message(chat_id, "Client with this number does not exists. Do you want to add it?", reply_markup=yes_no_markup())
                state["data"]["client_number"] = nospace(message.text)
                bot.register_next_step_handler(message, lambda msg: yes_no_answer(bot, msg))
                
        case 1:
            bot.send_message(chat_id, "Enter new client's number:", reply_markup=back_skip(state['old_data'][1]))
            state["step"] = 2
            bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))

        case 2:
            res = handle_back(bot, message, state, back_step=3)
            if res == "backing":
               return edit_client_steps(bot, message)
            elif len(lower_ns(message.text)) > 20:
                bot.send_message(chat_id, "Too many characters entered. (max is 20)", reply_markup=back_skip(state['old_data'][1]))
                return bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))
            state["data"]["client_number"] = None if lower_ns(message.text) == SK else nospace(message.text)
            state["step"] = 3
            bot.send_message(chat_id, "Enter new client's name:", reply_markup=back_skip(state['old_data'][2]))
            bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))

        case 3:
            res = handle_back(bot, message, state, back_step=2)
            if res == "backing":
               return edit_client_steps(bot, message)
            elif lower_ns(message.text) != SK and not is_name(titlecase(message.text)):
                bot.send_message(chat_id, "Please enter a valid name (letters, spaces, hyphens, apostrophes only) or 'skip':", reply_markup=back_skip(state['old_data'][2]))
                return bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))
            elif len(titlecase(message.text)) > 70:
                bot.send_message(chat_id, "Too many characters entered. (max is 70)", reply_markup=back_skip(state['old_data'][2]))
                return bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))
            state["data"]["name"] = None if lower_ns(message.text) == SK else titlecase(message.text)
            state["step"] = 4
            bot.send_message(chat_id, "Enter new client's surname:", reply_markup=back_skip(state['old_data'][3]))
            bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))

        case 4:
            res = handle_back(bot, message, state, back_step=2)
            if res == "backing":
               new_msg = SimpleNamespace(**vars(message))
               new_msg.text = state['data']['client_number'] if state['data']['client_number'] is not None else SK
               return edit_client_steps(bot, new_msg)
            elif lower_ns(message.text) != SK and not is_name(titlecase(message.text)):
                bot.send_message(chat_id, "Please enter a valid surname (letters, spaces, hyphens, apostrophes only) or 'skip':", state['old_data'][3])
                return bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))
            elif len(titlecase(message.text)) > 70:
                bot.send_message(chat_id, "Too many characters entered. (max is 70)", reply_markup=back_skip(state['old_data'][3]))
                return bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))
            state["data"]["surname"] = None if lower_ns(message.text) == SK else titlecase(message.text)
            state["step"] = 5
            bot.send_message(chat_id, "Enter new client's phone number:", reply_markup=back_skip(state['old_data'][4]))
            bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))

        case 5:
            res = handle_back(bot, message, state, back_step=2)
            if res == "backing":
               new_msg = SimpleNamespace(**vars(message))
               new_msg.text = state['data']['name'] if state['data']['name'] is not None else SK
               return edit_client_steps(bot, new_msg)
            elif lower_ns(message.text) != SK and nospace(message.text) != state['old_data'][4]:
                if not is_phone(message.text):
                    bot.send_message(chat_id,"Please enter a valid phone number", reply_markup=back_skip(state['old_data'][4]))
                    return bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))
                elif db.check_phone_exists(nospace(message.text)):
                    bot.send_message(chat_id, "This phone number is already associated with another client."
                                    "Please enter a different phone number or type 'skip':", reply_markup=back_skip(state['old_data'][4]))
                    return bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))
            elif len(lower_ns(message.text)) > 20:
                bot.send_message(chat_id, "Too many characters entered. (max is 20)", reply_markup=back_skip(state['old_data'][4]))
                return bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))
            state["data"]["phone_number"] = None if lower_ns(message.text) == SK else nospace(message.text)
            state["step"] = 6
            bot.send_message(chat_id, "Enter new status (active/inactive):", reply_markup=back_skip("status"))
            bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))
        case 6:
            res = handle_back(bot, message, state, back_step=2)
            if res == "backing":
               new_msg = SimpleNamespace(**vars(message))
               new_msg.text = state['data']['surname'] if state['data']['surname'] is not None else SK
               return edit_client_steps(bot, new_msg)
            if nospace(message.text) in [STATUS_ACTIVE, STATUS_INACTIVE, SK]:
                state["data"]["status"] = None if lower_ns(message.text) == SK  else nospace(message.text)
            else:
                bot.send_message(chat_id, "Please enter 'active', 'inactive' or 'skip':", reply_markup=back_skip())
                return bot.register_next_step_handler(message, lambda msg: edit_client_steps(bot, msg))
            old_client = db.show_client_in_db(state["old_data"][1])
            new_client = f"{state['data']['client_number'] if state['data']['client_number'] is not None else state['old_data'][1]} | " \
                            f"{state['data']['name'] if state['data']['name'] is not None else state['old_data'][2]} | " \
                            f"{state['data']['surname'] if state['data']['surname'] is not None else state['old_data'][3]} | " \
                            f"{state['data']['phone_number'] if state['data']['phone_number'] is not None else state['old_data'][4]} | " \
                            f"{state['data']['status'] if state['data']['status'] is not None else state['old_data'][-1]}"                   
            bot.send_message(chat_id, f"Do you want to change: \n {old_client} \n on: \n {new_client}  ?", reply_markup=yes_no_markup())
            bot.register_next_step_handler(message, lambda msg: yes_no_answer(bot, msg))
        case 7:
            if db.update_client_in_db(state["old_data"][1],state["data"]["client_number"],state["data"]["name"],state["data"]["surname"]
                                   ,state["data"]["phone_number"],state["data"]["status"]):
                bot.send_message(chat_id, "✅ Client updated!", reply_markup=rm_kb())
            else:
                bot.send_message(chat_id, "Failed to update client.", reply_markup=rm_kb())
            reset_state(chat_id)