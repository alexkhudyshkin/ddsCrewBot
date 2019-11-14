# -*- coding: utf-8 -*-
import config as cfg
import text_processing as tp
import time
import datetime
import database as db

dinner_vote_sum = dict()

# обновить глобальную переменную с временем обеда
@cfg.loglog(command='upd_din_time', type='bot')
def upd_din_time(cid, clear=False):
    # очищаем время обеда в конце дня
    if clear:
        dinner_vote_sum = dict()
    # пересчитываем время обеда в глобальной переменной
    cfg.show_din_time[cid] = str(cfg.settings[cid]['default_dinner_time'] + datetime.timedelta(minutes=dinner_vote_sum.get(cid,0)))[:-3]

# вернуть время обеда в datetime
@cfg.loglog(command='show_din_time', type='bot')
def show_din_time(cid):
    return cfg.settings[cid]['default_dinner_time'] + datetime.timedelta(minutes=dinner_vote_sum.get(cid,0))

# обработка голоса за обед
@cfg.loglog(command='vote_func', type='bot')
def vote_func(cid, user_id, vote_chat, bot, message):
    dinner_vote = db.sql_exec(db.sel_election_text, [cid, user_id])
    if len(dinner_vote) == 0:
        bot.reply_to(message, cfg.err_vote_msg)
    else:
        vote_db = dinner_vote[0][2]
        penalty_time = dinner_vote[0][3]
        final_elec_time = 0
        sign = 1
        
        if vote_chat != 0:
            sign = vote_chat / abs(vote_chat)
            final_elec_time = vote_chat - sign * penalty_time
        
        if abs(final_elec_time) > 25:
            final_elec_time = sign * 25
        
        if sign * final_elec_time < 0:
            final_elec_time = 0
        
        final_elec_time = datetime.timedelta(minutes=final_elec_time)
        #считаем сумму голосов отдельно от времени
        dinner_vote_sum[cid] = dinner_vote_sum.get(cid,0) + final_elec_time
            
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
        
            if abs(final_elec_time) > 25:
                final_elec_time = sign * 25
        
            if sign * final_elec_time < 0:
                final_elec_time = 0

            final_elec_time = datetime.timedelta(minutes=final_elec_time)
            # считаем сумму голосов отдельно от времени обеда
            dinner_vote_sum[cid] -= final_elec_time
            # обновляем итоговое время обеда
            upd_din_time(cid)
            bot.reply_to(message, cfg.revote_msg + additional_msg + cfg.show_din_time[cid])
        
        print('Время обеда', cfg.show_din_time[cid])
        db.sql_exec(db.upd_election_elec_text, [vote_chat, cid, user_id])

# пересчитать время обеда в оперативке после перезагрузки бота
@cfg.loglog(command='vote_recalc', type='bot')
def vote_recalc():
    dinner_vote = db.sql_exec(db.sel_all_election_text)
    for i in range(len(dinner_vote)):
        cid = dinner_vote[i][0]
        user_id = dinner_vote[i][1]
        vote_chat = dinner_vote[i][2]
        penalty_time = dinner_vote[i][3]
        final_elec_time = 0
        sign = 1
        
        if vote_chat != 0:
            sign = vote_chat / abs(vote_chat)
            final_elec_time = vote_chat - sign * penalty_time
        
        if abs(final_elec_time) > 25:
            final_elec_time = sign * 25
        
        if sign * final_elec_time < 0:
            final_elec_time = 0
        
        final_elec_time = datetime.timedelta(minutes=final_elec_time)
        # считаем сумму голосов отдельно от времени обеда
        dinner_vote_sum[cid] = dinner_vote_sum.get(cid,0) + final_elec_time
        # обновляем итоговое время обеда
        upd_din_time(cid)

# nsfw print function
@cfg.loglog(command='nsfw_print', type='bot')
def nsfw_print(message):
    bot.send_sticker(message.chat.id, cfg.sticker_dog_left)
    bot.send_message(message.chat.id, '!!! NOT SAFE FOR WORK !!!\n' * 3)
    bot.send_sticker(message.chat.id, random.choice(cfg.sticker_nsfw))
    bot.send_message(message.chat.id, '!!! NOT SAFE FOR WORK !!!\n' * 3)
    bot.send_sticker(message.chat.id, cfg.sticker_dog_right)

# пересчитываем сумму голосов в оперативке в случае перезагрузки бота в течение дня
vote_recalc()