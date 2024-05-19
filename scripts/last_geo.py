import psycopg2


def connect_to_db(dbname, user, password, host):
    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host)
    cur = conn.cursor()
    return conn, cur


def insert_last_geo(conn, cur):
    cur.execute("INSERT INTO car_washes (date, user_name, lat, lon, notification_time) "
                "VALUES ('2024-05-20', 'TestUser', 55.7558, 37.6173, '14:00:00');")
    conn.commit()


def get_last_geo(conn, cur):
    cur.execute("SELECT * FROM car_washes;")
    rows = cur.fetchall()
    for row in rows:
        print(row)


def update_last_geo(conn, cur):
    cur.execute("UPDATE car_washes SET user_name = 'UpdatedUser' WHERE user_name = 'TestUser';")
    conn.commit()


def close_connection(conn, cur):
    cur.close()
    conn.close()


def main():
    conn, cur = connect_to_db('wash_your_car_db', 'newuser', 'password', 'localhost')
    insert_last_geo(conn, cur)
    get_last_geo(conn, cur)
    update_last_geo(conn, cur)
    get_last_geo(conn, cur)
    close_connection(conn, cur)


if __name__ == '__main__':
    main()
