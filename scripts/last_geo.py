import psycopg2


def connect_to_db(dbname, user, password, host):
    try:
        conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host)
        cur = conn.cursor()
        return conn, cur
    except psycopg2.Error as e:
        print(f"Error connecting to the database: {e}")
        return None, None


def insert_last_geo(conn, cur, date, user_id, user_name, lat, lon, notification_time):
    try:
        cur.execute(
            "INSERT INTO car_washes (date, user_id, user_name, lat, lon, notification_time) "
            "VALUES (%s, %s, %s, %s, %s, %s);",
            (date, user_id, user_name, lat, lon, notification_time)
        )
        conn.commit()
    except psycopg2.Error as e:
        print(f"Error inserting last geo information: {e}")


def get_last_geo(cur, user_id):
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
        else:
            print(f"No records found for user_id {user_id}")
            return False
    except psycopg2.Error as e:
        print(f"Error getting last geo information: {e}")
        return None


def update_last_geo(conn, cur, user_id, new_lat, new_lon):
    try:
        cur.execute(
            "UPDATE car_washes SET lat = %s, lon = %s WHERE user_id = %s;",
            (new_lat, new_lon, user_id)
        )
        conn.commit()
        print(f"Successfully updated lat and lon for user_id {user_id}")
    except psycopg2.Error as e:
        print(f"Error updating last geo information: {e}")
        conn.rollback()


def close_connection_db(conn, cur):
    try:
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error closing connection: {e}")


def main():
    from functions import read_yaml
    conf = read_yaml('config.yml')
    conn, cur = connect_to_db(conf['db']['database_name'],
                              conf['db']['user_name'],
                              conf['db']['user_password'],
                              conf['db']['host'])
    if conn and cur:
        insert_last_geo(conn,
                        cur,
                        '2024-05-20',
                        '123321'
                        'TestUser',
                        55.7558,
                        37.6173,
                        '14:00:00')
        get_last_geo(cur)

        update_last_geo(conn, cur, 'UpdatedUser', 'TestUser')
        get_last_geo(cur)


if __name__ == '__main__':
    main()
