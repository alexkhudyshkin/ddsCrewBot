# -*- coding: utf-8 -*-

import sqlite3 as sql
import config as cfg
import datetime

ct_text = """CREATE TABLE IF NOT EXISTS PARTICIPANT
            (
            chat_id integer,
            participant_id integer,
            participant_first_name text,
            participant_last_name text,
            participant_username text
            );"""

ct_election_text = """CREATE TABLE IF NOT EXISTS ELECTION
            (
            chat_id integer,
            participant_id integer,
            elec_time integer,
            penalty_time integer,
            minus_flg integer
            );"""

ct_election_hist_text = """CREATE TABLE IF NOT EXISTS ELECTION_HIST
            (
            chat_id integer,
            participant_id integer,
            elec_time integer,
            penalty_time integer,
            minus_flg,
            election_date text
            );"""

ct_chatID_text = """CREATE TABLE IF NOT EXISTS CHAT_ID
            (
            chat_id integer
            );"""

ct_metadata_text = """CREATE TABLE IF NOT EXISTS METADATA
            (
            id_rk integer,
            operation integer,
            chat_id integer,
            participant_id integer,
            value integer,
            operation_date_from text,
            operation_date_to text,
            is_success_flg integer
            );"""

# ct_meme_text = """CREATE TABLE IF NOT EXISTS MEME
#             (
#             chat_id integer,
#             name text,
#             type text,
#             value text
#             );"""

ct_meme_text = """CREATE TABLE IF NOT EXISTS MEME
            (
            meme_id integer,
            chat_id integer,
            meme_name text,
            meme_type text,
            meme_value text
            );"""

ct_settings_text = """CREATE TABLE IF NOT EXISTS SETTINGS
            (
            chat_id integer,
            default_time_hour integer,
            default_time_minute integer,
            max_deviation integer,
            autodetect_vote_flg integer,
            lol_kek_flg integer,
            voronkov_flg integer,
            pidor_flg integer
            );"""

ins_lj_participant_election_text = """INSERT INTO ELECTION
            SELECT part.chat_id, part.participant_id,
            cast(0 as integer) as elec_time, cast(0 as integer) as penalty_time, cast(0 as integer) as minus_flg
            FROM
            PARTICIPANT as part LEFT JOIN ELECTION as elec
            on (part.chat_id = elec.chat_id and
            part.participant_id = elec.participant_id)
            WHERE elec.participant_id is NULL;"""

sel_all_penalty_time_text = """SELECT part.participant_username, elec.penalty_time, part.participant_id
            FROM ELECTION as elec JOIN PARTICIPANT as part
            on (part.chat_id = ? and part.chat_id = elec.chat_id and
            part.participant_id = elec.participant_id);"""

# судя по документации библиотеки, использовать ? более секурно, чем %*
ins_text = """INSERT INTO PARTICIPANT
            VALUES (?,?,?,?,?);"""

del_text = """DELETE FROM PARTICIPANT WHERE chat_id = ? and participant_id = ?;"""

del_election_text = """DELETE FROM ELECTION WHERE chat_id = ? and participant_id = ?;"""

# sel_all_text = """SELECT * FROM PARTICIPANT WHERE chat_id = ?;"""
sel_all_text = """SELECT participant_username, participant_id FROM PARTICIPANT WHERE chat_id = ?;"""

# sel_text = """SELECT * FROM PARTICIPANT WHERE chat_id = ? and participant_id = ?;"""
sel_text = """SELECT participant_username, participant_id
            FROM PARTICIPANT WHERE chat_id = ? and participant_id = ?;"""

sel_election_text = """SELECT * FROM ELECTION WHERE chat_id = ? and participant_id = ?;"""

# вытаскиваем текущие голоса и штрафы всех участников
sel_all_election_text = """SELECT * FROM ELECTION; """

# вытаскиваем чаты которые голосуют
sel_chats_election_text = """SELECT DISTINCT chat_id FROM ELECTION; """

upd_election_elec_text = """UPDATE ELECTION
            SET elec_time = ?
            WHERE chat_id = ? and participant_id = ?;"""

upd_election_penalty_text = """UPDATE ELECTION
            SET penalty_time = ?
            WHERE chat_id = ? and participant_id = ?;"""

reset_election_time_text = """UPDATE ELECTION SET elec_time = ?;"""

colect_election_hist_text = """INSERT INTO ELECTION_HIST
            SELECT elec.chat_id, elec.participant_id, elec.elec_time, elec.penalty_time,
            cast(? as text) FROM ELECTION as elc;"""

sel_nonvoted_users_text = """SELECT part.participant_username
            FROM ELECTION as elec JOIN PARTICIPANT as part
            on (part.chat_id = elec.chat_id and
            part.participant_id = elec.participant_id)
            WHERE elec.elec_time = 0 and elec.chat_id = ?;"""

sel_chatID_text = """SELECT * FROM CHAT_ID WHERE chat_id = ?;"""

ins_chatID_text = """INSERT INTO CHAT_ID
            VALUES (?);"""

del_chatID_text = """DELETE FROM CHAT_ID WHERE chat_id = ?;"""

sel_all_chatID_text = """SELECT * FROM CHAT_ID;"""

ins_operation_meta_text = """INSERT INTO METADATA
            VALUES (?,?,?,?,?,?,?,?)"""

sel_max_id_rk_meta_text = """SELECT max(id_rk) FROM METADATA"""

sel_meta_by_rk = """SELECT * FROM METADATA WHERE id_rk = ?"""

sel_operation_meta_text = """SELECT * FROM METADATA
            WHERE operation = ? and is_success_flg = ?"""

upd_operation_meta_text = """UPDATE METADATA
            SET is_success_flg = ?
            WHERE id_rk = ?"""

sel_meme_name_text = """SELECT meme_type, meme_value FROM MEME WHERE chat_id = ? AND meme_name = ?;"""

sel_meme_id_text = """SELECT meme_type, meme_value FROM MEME WHERE chat_id = ? AND meme_id = ?;"""

sel_meme_in_chat_text = """SELECT meme_id, meme_name FROM MEME WHERE chat_id = ?"""

# ins_meme_text = """INSERT INTO MEME
#             VALUES (?,?,?,?);"""

ins_meme_text = """INSERT INTO MEME
            VALUES (?,?,?,?,?);"""

del_meme_name_text = """DELETE FROM MEME WHERE chat_id = ? AND meme_name = ?;"""

del_meme_id_text = """DELETE FROM MEME WHERE chat_id = ? AND meme_id = ?;"""

sel_max_meme_id_text = """SELECT max(meme_id) FROM MEME
                          WHERE chat_id = ?
                          group by chat_id"""

#простая проверка в базе чего угодно с возвратом true/false
@cfg.loglog(command='boolean_select', type='db_common')
def boolean_select(query,chat_id,user_id=0):
    try:
        db = sql.connect(cfg.db_name)
        cursor = db.cursor()
        if user_id == 0:
            cursor.execute(query, [chat_id])
        else:
            cursor.execute(query, [chat_id, user_id])
            
        if len(cursor.fetchall()) != 0:
            return True
        else:
            return False
    except Exception as e:
        print('***ERROR: boolean_select failed!***')
        print('Exception text: ' + str(e))
        return False
        
#является подписчиком
is_subscriber_text = """SELECT 1 FROM PARTICIPANT WHERE chat_id = ? and participant_id = ?;"""
def is_subscriber(chat_id,user_id):
    return boolean_select(is_subscriber_text,chat_id,user_id)

#имеет штрафы
has_penalty_text = """SELECT 1 FROM ELECTION WHERE chat_id = ? and participant_id = ? and penalty_time > 0;"""
def has_penalty(chat_id,user_id):
    return boolean_select(has_penalty_text,chat_id,user_id)

#не обедает сегодня
is_minus_text = """SELECT 1 FROM ELECTION WHERE chat_id = ? and participant_id = ? and minus_flg = 1;"""
def is_minus(chat_id,user_id):
    return boolean_select(is_minus_text,chat_id,user_id)

# заглушка до реализации пидора в боте
is_pidor_text = """___"""
def is_pidor(chat_id,user_id):
    #return boolean_select(is_pidor,chat_id,user_id)
    return False

#вставка настроек по умолчанию
check_if_settings_exist_text = """SELECT 1 FROM SETTINGS WHERE chat_id = ?;"""
ins_default_settings_text = """INSERT INTO SETTINGS VALUES (?,?,?,?,?,?,?,?);"""
@cfg.loglog(command='default_settings', type='settings')
def default_settings(chat_id):
    try:
        # не добавляем дубли
        if boolean_select(check_if_settings_exist_text, chat_id):
            pass
        else:
            # добавляем в базу настройки времени по умолчанию
            db = sql.connect(cfg.db_name)
            cursor = db.cursor()
            cursor.execute(ins_default_settings_text, \
                           [chat_id, \
                           cfg.dinner_default_time[0], \
                           cfg.dinner_default_time[1], \
                           cfg.dinner_default_plusminus_time, \
                           cfg.autodetect_vote_default, \
                           cfg.lol_kek_default, \
                           cfg.voronkov_default, \
                           cfg.pidor_default] )
            db.commit()
    except Exception as e:
        print('***ERROR: default_settings failed!***')
        print('Exception text: ' + str(e))

#обновление среднего времени
update_time_setting_text = """UPDATE SETTINGS 
                           SET default_time_hour = ?, 
                           default_time_minute = ? 
                           WHERE chat_id = ?; """
@cfg.loglog(command='update_time_setting', type='settings')
def update_time_setting(chat_id,hour,minute):
    db = sql.connect(cfg.db_name)
    cursor = db.cursor()
    cursor.execute(update_time_setting_text, [hour, minute, chat_id])
    db.commit()

#обновление времени отклонения
update_deviation_setting_text = """UPDATE SETTINGS 
                           SET max_deviation = ? 
                           WHERE chat_id = ?; """
@cfg.loglog(command='update_deviation_setting', type='settings')
def update_deviation_setting(chat_id,minutes):
    db = sql.connect(cfg.db_name)
    cursor = db.cursor()
    cursor.execute(update_deviation_setting_text, [minutes, chat_id])
    db.commit()

#обновление флаговых настроек
update_flg_setting_text = "UPDATE SETTINGS SET {} = {} WHERE chat_id = {};"
@cfg.loglog(command='update_flg_setting', type='settings')
def update_flg_setting(chat_id,setting,flg):
    try:
        db = sql.connect(cfg.db_name)
        cursor = db.cursor()
        if setting in cfg.settings_todb_dict and flg in cfg.flg_dict:
            cursor.execute(update_flg_setting_text.format(cfg.settings_todb_dict[setting], cfg.flg_dict[flg], chat_id))
            db.commit()
    except Exception as e:
        print('***ERROR: update_flg_setting failed!***')
        print('Exception text: ' + str(e))

# вытаскиваем настройки по умолчанию в чатах
select_settings_text = """SELECT chat_id, default_time_hour, default_time_minute, 
                  max_deviation, autodetect_vote_flg, lol_kek_flg, voronkov_flg, pidor_flg
                  FROM SETTINGS; """
def select_settings():
    try:
        settings = dict()
        db = sql.connect(cfg.db_name)
        cursor = db.cursor()
        cursor.execute(select_settings_text)
        res = cursor.fetchall()
        for i in range(len(res)):
            settings[res[i][0]] = {"default_dinner_time": datetime.timedelta(hours=res[i][1], minutes=res[i][2]) \
                                    ,"max_deviation": datetime.timedelta(minutes=res[i][3]) \
                                    ,"autodetect_vote": res[i][4] \
                                    ,"lol_kek": res[i][5] \
                                    ,"voronkov": res[i][6] \
                                    ,"pidor": res[i][7] }
        return settings
    except Exception as e: 
        print('***ERROR: select_settings failed!***')
        print('Exception text: ' + str(e))
        return 'ERROR!'
        
# создать таблицу
@cfg.loglog(command='create_table', type='ct')
def create_table():
    db = sql.connect(cfg.db_name)
    cursor = db.cursor()
    # таблица участников
    cursor.execute(ct_text)
    # таблица для голосования
    cursor.execute(ct_election_text)
    # таблица истории голосований
    cursor.execute(ct_election_hist_text)
    # таблица чатов, подписавшихся на рассылку разных сообщений ботом
    cursor.execute(ct_chatID_text)
    # таблица метаданных операций
    cursor.execute(ct_metadata_text)
    # таблица мемов
    cursor.execute(ct_meme_text)
    # таблица настроек
    cursor.execute(ct_settings_text)
    db.commit()


# выполнить sql запрос
@cfg.loglog(command='sql_exec', type='db_exec')
def sql_exec(exec_text, params):
    try:
        db = sql.connect(cfg.db_name)
        cursor = db.cursor()
        cursor.execute(exec_text, params)
        db.commit()
        return cursor.fetchall()
    except Exception:
        return 'ERROR!'


# очистка таблицы голосования, ТОЛЬКО ДЛЯ ТЕСТИРОВАНИЯ!!!
# sql_exec(reset_election_time_text, [0])
# sql_exec("""UPDATE ELECTION SET penalty_time = ?;""", [0])
# print(sql_exec("""DELETE FROM ELECTION_HIST""", []))

# print(sql_exec("""DROP TABLE ELECTION_HIST""", []))
# print(sql_exec(colect_election_hist_text, ['2018-09-06']))
# print(sql_exec("""SELECT * FROM ELECTION_HIST""", []))

# sql_exec("""DROP TABLE METADATA""", [])


# вставить данные в таблицу participant and election
@cfg.loglog(command='insert_into_participants', type='db_common')
def insert_into_participants(chat_id, user):
    db = sql.connect(cfg.db_name)
    cursor = db.cursor()

    # не добавляем дубли
    cursor.execute(sel_text, [chat_id, user.id])
    if len(cursor.fetchall()) != 0:
        return -1

    cursor.execute(ins_text, [chat_id, user.id, user.first_name, user.last_name, user.username])
    # обновляем таблицу голосующих за обед
    cursor.execute(ins_lj_participant_election_text)
    db.commit()
    return 1


# удалить данные из таблиц participant and election по конкретному чату-клиенту
@cfg.loglog(command='delete_from_participants', type='db_common')
def delete_from_participants(chat_id, user_id):
    db = sql.connect(cfg.db_name)
    cursor = db.cursor()
    cursor.execute(del_text, [chat_id, user_id])
    # удаляем участника из таблицы голосующих за обед
    cursor.execute(del_election_text, [chat_id, user_id])
    db.commit()


# вставить данные в таблицу participant and election
@cfg.loglog(command='insert_into_chatID', type='sql_chatID')
def insert_into_chatID(chat_id):
    db = sql.connect(cfg.db_name)
    cursor = db.cursor()

    # не добавляем дубли
    cursor.execute(sel_chatID_text, [chat_id])
    if len(cursor.fetchall()) != 0:
        return -1

    cursor.execute(ins_chatID_text, [chat_id])
    db.commit()
    # обновляем список чатов для использования ботом
    cfg.subscribed_chats_transform(sql_exec(sel_all_chatID_text, []))
    return 1


# удалить данные из таблиц participant and election по конкретному чату-клиенту
@cfg.loglog(command='delete_from_chatID', type='sql_chatID')
def delete_from_chatID(chat_id):
    db = sql.connect(cfg.db_name)
    cursor = db.cursor()
    cursor.execute(del_chatID_text, [chat_id])
    db.commit()
    # обновляем список чатов для использования ботом
    cfg.subscribed_chats_transform(sql_exec(sel_all_chatID_text, []))


# создать таблицы, если их нет
create_table()

# обнуляем таблицу голосования
sql_exec(reset_election_time_text, [0])

# обновляем список чатов, чьи сообщения бот может читать
cfg.subscribed_chats_transform(sql_exec(sel_all_chatID_text, []))

# вытаскиваем максимальный id метаданных
max_id_rk = sql_exec(sel_max_id_rk_meta_text, [])
if max_id_rk[0][0] is None:
    max_id_rk = [(0,)]
cfg.max_id_rk = int(max_id_rk[0][0]) + 1


# db = sql.connect(cfg.db_name)
# cursor = db.cursor()
# cursor.execute('''select * from participant;''')
# cursor.execute('''select * from ELECTION;''')
# print(cursor.fetchall())
# db.commit()
