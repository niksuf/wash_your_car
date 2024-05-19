import psycopg2

# Подключение к базе данных
conn = psycopg2.connect(dbname='wash_your_car_db', user='newuser', password='password', host='localhost')
cur = conn.cursor()

# Переключение на нового пользователя
# cur.execute("\c wash_your_car_db newuser")

# Проверка вставки
cur.execute("INSERT INTO car_washes (date, user_name, lat, lon, notification_time) VALUES ('2024-05-20', 'TestUser', 55.7558, 37.6173, '14:00:00');")
conn.commit()

# Проверка выборки
cur.execute("SELECT * FROM car_washes;")
rows = cur.fetchall()
for row in rows:
    print(row)

# Проверка обновления
cur.execute("UPDATE car_washes SET user_name = 'UpdatedUser' WHERE user_name = 'TestUser';")
conn.commit()

# Закрытие соединения с базой данных
cur.close()
conn.close()
