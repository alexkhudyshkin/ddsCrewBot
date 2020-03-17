# -*- coding: utf-8 -*-
import config as cfg
import datetime
import database as db
import random


# обновление CHAT_ID в базе
def updateChatId(e, cid):
    if e.args[0].find('Bad Request: group chat was upgraded to a supergroup chat') != -1:
        import json as js

        d = js.loads(str(e.args[0].split('\n')[1][3:-2]))
        newCid = d['parameters']['migrate_to_chat_id']

        print('!!! CHAT WITH CHAT_ID {} MOVED TO CHAT_ID {} !!!'.format(cid, newCid))

        cfg.bot.send_message(newCid, cfg.group_to_supergroup_text)

        if not(db.boolean_select(db.check_if_settings_exist_text, [cid])):
            db.sql_exec(db.ins_settings_copy_text, [newCid, cid])
            cfg.settings[newCid] = cfg.settings[cid].copy()
            cfg.show_din_time[newCid] = cfg.show_din_time[cid]

        db.delete_from_chatID(cid)

        return newCid


def getSettings(cid, setting=None):
    try:
        return cfg.settings[cid][setting] if setting else cfg.settings[cid]
    except Exception as e:
        print(e)
        if e.__class__.__name__ == 'ApiException':
            newCid = updateChatId(e, cid)
            return cfg.settings[newCid][setting] if setting else cfg.settings[newCid]


def sendMessage(bot, cid, msg, parse_mode='HTML'):
    try:
        bot.send_message(cid, msg, parse_mode=parse_mode)
    except Exception as e:
        print(e)
        if e.__class__.__name__ == 'ApiException':
            newCid = updateChatId(e, cid)
            bot.send_message(newCid, msg, parse_mode=parse_mode)


# вернуть время обеда в datetime
def calc_show_din_time(cid):
    return getSettings(cid, 'default_dinner_time') + datetime.timedelta(minutes=dinner_vote_sum.get(cid, 0))


# обновить глобальную переменную с временем обеда
def upd_din_time(cid=False):
    # указываем на использование глобальной переменной, иначе не работает
    global dinner_vote_sum
    if cid is False:
        # очищаем время голосов за обед в конце дня
        for chat in cfg.show_din_time.keys():
            dinner_vote_sum[chat] = 0
            cfg.show_din_time[chat] = str(getSettings(chat, 'default_dinner_time'))[:-3]
    else:
        # пересчитываем время обеда в глобальной переменной
        cfg.show_din_time[cid] = str(calc_show_din_time(cid))[:-3]


# обработка голоса за обед
def vote_func(vote_chat, bot, message):
    cid = message.chat.id
    user_id = message.from_user.id
    # TODO: в рамках рефакторинга отказаться от обращения к базе в целях оптимизации, т.к. оно здесь только ради получения предыдущего голоса. Штрафы есть в оперативке
    dinner_vote = db.sql_exec(db.sel_election_text, [cid, user_id])
    penalty_time = dinner_vote[0][3]
    # определяем максимальный голос пользователя. Если он меньше нуля, то ноль
    if penalty_time > 0:
        max_vote = max(0, cfg.votemax_with_penalty[cid] - penalty_time)
    else:
        max_vote = max(0, cfg.votemax[cid] - penalty_time)
    # проверяем, что голос входит в рамки допустимого голосования
    if abs(vote_chat) > max_vote:
        bot.reply_to(message, cfg.err_vote_limit.format(max_vote))
    else:
        vote_db = dinner_vote[0][2]
        final_elec_time = 0
        sign = 1

        if vote_chat != 0:
            sign = vote_chat / abs(vote_chat)
            final_elec_time = vote_chat - sign * penalty_time

        if abs(final_elec_time) > getSettings(cid, 'max_deviation').seconds // 60:
            final_elec_time = sign * getSettings(cid, 'max_deviation').seconds // 60

        if sign * final_elec_time < 0:
            final_elec_time = 0

        # final_elec_time = datetime.timedelta(minutes=final_elec_time)
        # считаем сумму голосов отдельно от времени
        dinner_vote_sum[cid] = dinner_vote_sum.get(cid, 0) + final_elec_time

        additional_msg = ''
        if penalty_time != 0:
            additional_msg = 'с учётом штрафов '

        # голосование или переголосование
        if int(vote_db) == 0:
            # обновляем итоговое время обеда
            upd_din_time(cid)
            bot.reply_to(message, cfg.vote_msg + additional_msg + cfg.show_din_time[cid])
        else:
            final_elec_time = 0
            prev_vote_db = int(vote_db)
            sign = 1

            if prev_vote_db != 0:
                sign = prev_vote_db / abs(prev_vote_db)
                final_elec_time = prev_vote_db - sign * penalty_time

            if abs(final_elec_time) > getSettings(cid, 'max_deviation').seconds // 60:
                final_elec_time = sign * getSettings(cid, 'max_deviation').seconds // 60

            if sign * final_elec_time < 0:
                final_elec_time = 0

            # final_elec_time = datetime.timedelta(minutes=final_elec_time)
            # считаем сумму голосов отдельно от времени обеда
            dinner_vote_sum[cid] -= final_elec_time
            # обновляем итоговое время обеда
            upd_din_time(cid)
            bot.reply_to(message, cfg.revote_msg + additional_msg + cfg.show_din_time[cid])

        print('Время обеда', cfg.show_din_time[cid])
        db.sql_exec(db.upd_election_elec_text, [vote_chat, cid, user_id])


# пересчитать время обеда в оперативке после перезагрузки бота
# @cfg.loglog(command='vote_recalc', type='bot')
# def vote_recalc():
#     dinner_vote = db.sql_exec(db.sel_all_election_text, [])
#     for i in range(len(dinner_vote)):
#         cid = dinner_vote[i][0]
#         # user_id = dinner_vote[i][1]
#         vote_chat = dinner_vote[i][2]
#         penalty_time = dinner_vote[i][3]
#         final_elec_time = 0
#         sign = 1

#         if vote_chat != 0:
#             sign = vote_chat / abs(vote_chat)
#             final_elec_time = vote_chat - sign * penalty_time

#         if abs(final_elec_time) > 25:
#             final_elec_time = sign * 25

#         if sign * final_elec_time < 0:
#             final_elec_time = 0

#         # final_elec_time = datetime.timedelta(minutes=final_elec_time)
#         # считаем сумму голосов отдельно от времени обеда
#         dinner_vote_sum[cid] = dinner_vote_sum.get(cid, 0) + final_elec_time
#         # обновляем итоговое время обеда
#         upd_din_time(cid)


# nsfw print function
def nsfw_print(cid, bot):
    bot.send_sticker(cid, cfg.sticker_dog_left)
    bot.send_message(cid, '!!! NOT SAFE FOR WORK !!!\n' * 3)
    bot.send_sticker(cid, random.choice(cfg.sticker_nsfw))
    bot.send_message(cid, '!!! NOT SAFE FOR WORK !!!\n' * 3)
    bot.send_sticker(cid, cfg.sticker_dog_right)


# функция добавления мема
def meme_add_processing(message, meme_type, bot):
    # /meme_add /https... meme_name | /meme_add meme_name
    cid = message.chat.id
    bot.send_chat_action(cid, 'typing')

    query = None
    if meme_type in ('photo', 'video'):
        query = message.caption.strip().split()
    else:
        query = message.text.strip().split()

    meme_name = query[-1].strip().lower()

    mem = db.sql_exec(db.sel_meme_name_text, [cid, meme_name])

    if len(mem) != 0:
        bot.send_message(cid, cfg.meme_dict_text['add_exist_error'].format(meme_name))
        return

    curr_max_meme_id = db.sql_exec(db.sel_max_meme_id_text, [cid])
    if curr_max_meme_id == []:
        curr_max_meme_id = 1
    else:
        curr_max_meme_id = int(curr_max_meme_id[0][0]) + 1

    if meme_name.isdigit() is True:
        bot.send_message(cid, cfg.meme_dict_text['add_digital_name_error'])
        return

    res = None
    if meme_type == 'photo':
        if len(query) == 2:
            res = db.sql_exec(db.ins_meme_text, [curr_max_meme_id, cid, meme_name, meme_type,
                                                 message.json['photo'][-1]['file_id']])
        else:
            bot.send_message(cid, cfg.meme_dict_text['add_media_query_error'])
            return
    elif meme_type == 'video':
        if len(query) == 2:
            res = db.sql_exec(db.ins_meme_text, [curr_max_meme_id, cid, meme_name, meme_type,
                                                 message.json['video']['file_id']])
        else:
            bot.send_message(cid, cfg.meme_dict_text['add_media_query_error'])
            return
    elif meme_type == 'link':
        if len(query) == 3:
            res = db.sql_exec(db.ins_meme_text, [curr_max_meme_id, cid, meme_name, 'link',
                                                 query[1].strip()])
        else:
            bot.send_message(cid, cfg.meme_dict_text['add_link_query_error'])
            return

    if res is not None:
        bot.send_message(cid, cfg.meme_dict_text['add_success'].format(meme_name))
    else:
        bot.send_message(cid, cfg.meme_dict_text['add_unknown_error'])


# расчёт максимального голоса для чата
def vote_max_calc(cid):
    deviation = getSettings(cid, 'max_deviation').seconds // 60
    # ведём учёт пользователей которые писали минус
    # также проводим преобразование users_minus, чтобы обращение не падало
    cfg.users_minus[cid] = db.normalize_output(db.sql_exec(db.sel_minus_text, [cid]))
    # не допускаем деление на ноль
    if cfg.dinner_cnt[cid] > 1:
        # считаем по формуле из документации к доработке ШТРАФ 2.0, раздельно для людей со штрафами и без
        cfg.votemax[cid] = (deviation - (deviation * cfg.users_penalty_cnt[cid] / cfg.dinner_cnt[cid]) + cfg.penalty_sum[cid]) / (cfg.dinner_cnt[cid] - cfg.users_penalty_cnt[cid])
        cfg.votemax_with_penalty[cid] = deviation / cfg.dinner_cnt[cid]
    else:
        # если подписчиков не осталось, votemax=deviation
        cfg.votemax[cid] = deviation
        cfg.votemax_with_penalty[cid] = deviation


# сброс настроек параметров голосования
def vote_params_reset():
    vote_params_tmp = db.sql_exec(db.sel_vote_params_text, [])
    for chats in vote_params_tmp:
        # кол-во подписчиков в каждом чате по отдельности
        cfg.dinner_cnt[chats[0]] = chats[1]
        # сумма штрафов в каждом чате по отдельности
        cfg.penalty_sum[chats[0]] = chats[2]
        # кол-во людей со штрафами в каждом чате по отдельности
        cfg.users_penalty_cnt[chats[0]] = chats[3]
    
    # заполняем штрафы пользователей в оперативке
    penalty_tmp = db.sql_exec(db.sel_penalty_text, [])
    for users in penalty_tmp:
        cfg.penalty[users[0]] = cfg.penalty.get(users[0], {users[1]: users[2]})
        cfg.penalty[users[0]][users[1]] = users[2]

    for chats in cfg.chat_voters:
        # считаем votemax
        vote_max_calc(chats)


# сброс настроек параметров голосования для выбранного чата [и пользователя]
def vote_params_chat_reset(cid, uid=False):
    # сброс данных о голосовании в базе
    if uid is False:
        db.sql_exec(db.upd_reset_elec_chat_text, [cid])
    else:
        db.sql_exec(db.upd_reset_elec_user_text, [cid, uid])
    chat_params = db.sql_exec(db.sel_vote_params_chat_text, [cid])[0]
    # кол-во подписчиков в каждом чате по отдельности
    cfg.dinner_cnt[chat_params[0]] = chat_params[1]
    # сумма штрафов в каждом чате по отдельности
    cfg.penalty_sum[chat_params[0]] = chat_params[2]
    # кол-во людей со штрафами в каждом чате по отдельности
    cfg.users_penalty_cnt[chat_params[0]] = chat_params[3]    
    # пересчёт макс.голоса
    vote_max_calc(cid)
    # сброс голосований в оперативке
    dinner_vote_sum[cid] = 0
    upd_din_time(cid)


# обработка отказа от обеда
def dinner_minus(cid, uid, recalc_minutes=False):
    # уменьшаем количество голосующих в чате
    cfg.dinner_cnt[cid] -= 1
    db.sql_exec(db.upd_minus_text, [cid, uid])
    # пересчитываем макс.голос
    vote_max_calc(cid)
    # пересчитываем время обеда если пользователь проголосовал до минуса
    if recalc_minutes is not False:
        dinner_vote_sum[cid] -= recalc_minutes
        upd_din_time(cid)


# проверка возможности голосования по времени и дате
def vote_time_check(cid):
    if cid not in cfg.chat_voters: # TODO: эту проверку надо применить на другие команды, например penalty, dinner
        return cfg.no_subscribers_err
    # закомментировать строки ниже для тестирования
    # проверка что не выходной и не праздник
    if datetime.datetime.today().weekday() in (5, 6) or datetime.datetime.today() in cfg.ru_holidays:
        return cfg.no_dinner_today_err
    # проверка что время голосования не окончено
    # TODO: учёт часовых поясов ???
    if datetime.datetime.today().hour > getSettings(cid, 'elec_end_hour'):
        return cfg.too_late_err


# проверка, может ли пользователь голосовать
def user_vote_check(cid, uid):
    if db.is_subscriber(cid, uid) is False:
        return cfg.err_vote_msg
    vote_time_check_err = vote_time_check(cid)
    if vote_time_check_err:
        return vote_time_check_err
    # если минусовал
    if db.is_minus(cid, uid):
        # и сегодня уже кто-то голосовал, то запретить голосовать
        if db.sql_exec(db.check_chat_vote_text, [cid])[0][0] > 0:
            return cfg.err_minus_vote_msg
        # иначе сбросить минусы и дать проголосовать (механизм камбека)
        else:
            vote_params_chat_reset(cid, uid)


# преобразовать username в user_id 
def username_to_id(username):
    user_id = db.sql_exec(db.sel_uname_from_id_text, [username])
    if user_id:
        return user_id[0][0]


# отобразить максимальные голоса пользователей в чате
def maxvote_cmd(cid):
    count_plus = 0
    count_minus = 0
    result = ""
    result_plus = "Доступное число минут для голосования сегодня:\n"
    result_minus = "\nНе голосуют:\n"
    # пробегаемся по штрафам, т.к. maxvote для чата мы знаем и на итоговый голос влияют только штрафы
    for users in cfg.penalty[cid]:
        # показываем макс голос для голосующих пользователей
        if users not in cfg.users_minus[cid]:
            if cfg.penalty[cid][users] > 0:
                votemax_tmp = cfg.votemax_with_penalty[cid]
            else:
                votemax_tmp = cfg.votemax[cid]
            result_plus += cfg.maxvote_text.format(users, str(int(max(0, votemax_tmp - cfg.penalty[cid][users]))))
            count_plus += 1
        # показываем макс голос для минусанувших пользователей
        else:
            count_minus += 1
            result_minus += cfg.maxvote_minus_text.format(users)
    if count_plus > 0:
        result += result_plus
    if count_minus > 0:
        result += result_minus
    return result


dinner_vote_sum = {}
# пересчитываем сумму голосов в оперативке в случае перезагрузки бота в течение дня
# vote_recalc()
# записываем в оперативку параметры голосования
vote_params_reset()