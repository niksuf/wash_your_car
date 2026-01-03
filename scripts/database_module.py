"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Функциональность для взаимодействия с БД
"""

import psycopg2


def connect_to_db(dbname, user, password, host) -> tuple:
    """ Функция для подключения к БД """
    try:
        conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host)
        cur = conn.cursor()
        return conn, cur
    except psycopg2.Error as error:
        print(f"Error connecting to the database: {error}")
        return None, None


def close_connection_db(conn, cur) -> None:
    """ Функция закрывает подключение к БД """
    try:
        cur.close()
        conn.close()
    except Exception as error:
        print(f"Error closing connection: {error}")
