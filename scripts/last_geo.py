"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Функциональность для использования последней геопозиции.
Вся информация хранится в БД postgres
"""

import psycopg2


def check_last_geo(cur, user_id) -> bool | None:
    """
    Функция принимает курсор и user_id
    Ищет есть ли уже запись у пользователя в таблице
    Функция возвращает:
        True - запись найдена
        False - запись не найдена
        None - если возникла ошибка
    """
    try:
        cur.execute("SELECT * FROM car_washes WHERE user_id = %s;", (user_id,))
        rows = cur.fetchall()
        if rows:
            print(f"Found {len(rows)} records for user_id {user_id}:")
            for row in rows:
                print(row)
            return True
        print(f"No records found for user_id {user_id}")
        return False
    except psycopg2.Error as error:
        print(f"Error getting last geo information: {error}")
        return None


def get_last_geo(cur, user_id) -> tuple:
    """
    Функция достает из БД последнюю использованную геопозицию
    """
    try:
        cur.execute("SELECT lat, lon FROM car_washes WHERE user_id = %s "
                    "ORDER BY date DESC, notification_time DESC LIMIT 1;", (user_id,))
        result = cur.fetchone()
        if result:
            lat, lon = result
            return lat, lon
        return None, None
    except psycopg2.Error as error:
        print(f"Error getting last geo information: {error}")
        return None, None


def insert_last_geo(conn, cur, date, user_id, user_name, lat, lon, notification_time) -> None:
    """
    Функция записывает последнюю отправленную
    геопозицию в БД (если впервые отправлена)
    """
    try:
        cur.execute(
            "INSERT INTO car_washes (date, user_id, user_name, lat, lon, notification_time) "
            "VALUES (%s, %s, %s, %s, %s, %s);",
            (date, user_id, user_name, lat, lon, notification_time)
        )
        conn.commit()
    except psycopg2.Error as error:
        print(f"Error inserting last geo information: {error}")


def update_last_geo(conn, cur, user_id, new_lat, new_lon) -> None:
    """
    Функция обновляет в БД последнюю отправленную геопозицию
    """
    try:
        cur.execute(
            "UPDATE car_washes SET lat = %s, lon = %s WHERE user_id = %s;",
            (new_lat, new_lon, user_id)
        )
        conn.commit()
        print(f"Successfully updated lat and lon for user_id {user_id}")
    except psycopg2.Error as error:
        print(f"Error updating last geo information: {error}")
        conn.rollback()
