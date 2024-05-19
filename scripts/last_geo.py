import psycopg2
from contextlib import closing


def connect_to_db(dbname, user, password, host):
    try:
        conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host)
        cur = conn.cursor()
        return closing(conn), closing(cur)
    except psycopg2.Error as e:
        print(f"Error connecting to the database: {e}")
        return None, None


def insert_last_geo(conn, cur, date, user_name, lat, lon, notification_time):
    try:
        cur.execute(
            "INSERT INTO car_washes (date, user_name, lat, lon, notification_time) "
            "VALUES (%s, %s, %s, %s, %s);",
            (date, user_name, lat, lon, notification_time)
        )
        conn.commit()
    except psycopg2.Error as e:
        print(f"Error inserting last geo information: {e}")


def get_last_geo(cur):
    try:
        cur.execute("SELECT * FROM car_washes;")
        rows = cur.fetchall()
        for row in rows:
            print(row)
        print('\n')
    except psycopg2.Error as e:
        print(f"Error getting last geo information: {e}")


def update_last_geo(conn, cur, new_user_name, old_user_name):
    try:
        cur.execute(
            "UPDATE car_washes SET user_name = %s WHERE user_name = %s;",
            (new_user_name, old_user_name)
        )
        conn.commit()
    except psycopg2.Error as e:
        print(f"Error updating last geo information: {e}")


def main():
    with connect_to_db('wash_your_car_db',
                       'newuser',
                       'password',
                       'localhost') as (conn, cur):
        if conn and cur:
            insert_last_geo(conn,
                            cur,
                            '2024-05-20',
                            'TestUser',
                            55.7558,
                            37.6173,
                            '14:00:00')
            get_last_geo(cur)

            update_last_geo(conn, cur, 'UpdatedUser', 'TestUser')
            get_last_geo(cur)


if __name__ == '__main__':
    main()
