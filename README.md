# Wash your car
Wash your car - телеграм бот, который по запросу анализирует погоду (используется OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по следующей [ссылке](https://t.me/worth_wash_car_bot "бот").

## Создание таблиц
```
-- Таблица для хранения прогнозов
CREATE TABLE forecasts (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    date DATE NOT NULL,
    weather_data JSONB,           -- Данные погоды
    recommendation TEXT,          -- Рекомендация ('wash'/'dont_wash')
    message_id INTEGER,           -- ID сообщения в Telegram
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица для оценок пользователей
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    forecast_id INTEGER REFERENCES forecasts(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    is_positive BOOLEAN,          -- TRUE = лайк, FALSE = дизлайк
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(forecast_id, user_id)  -- Одна оценка на прогноз
);
```
