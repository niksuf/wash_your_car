"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Функциональность для взаимодействия с БД
"""

import psycopg2
import logging
from psycopg2.extras import DictCursor
import json
from datetime import datetime
from typing import List, Dict, Any

import logger

logger.setup_logging()


def connect_to_db(dbname, user, password, host) -> tuple:
    """ Функция для подключения к БД """
    try:
        conn = psycopg2.connect(
            dbname=dbname, 
            user=user, 
            password=password, 
            host=host,
            cursor_factory=DictCursor
        )
        cur = conn.cursor()
        return conn, cur
    except psycopg2.Error as error:
        logging.error(f"Error connecting to the database: {error}")
        return None, None


def close_connection_db(conn, cur) -> None:
    """ Функция закрывает подключение к БД """
    try:
        cur.close()
        conn.close()
    except Exception as error:
        logging.error(f"Error closing connection: {error}")


def save_donation(db_params: dict, donation_data: dict) -> bool:
    """
    Сохранение информации о донате в БД
    
    Args:
        db_params: Параметры подключения к БД
        donation_data: Данные доната
        
    Returns:
        True если успешно, False если ошибка
    """
    conn = None
    cur = None
    
    try:
        conn, cur = connect_to_db(
            db_params['dbname'],
            db_params['user'],
            db_params['password'],
            db_params['host']
        )
        
        if conn is None or cur is None:
            return False
        
        query = """
        INSERT INTO donations 
        (user_id, username, amount, currency, payment_system, payment_id, status, metadata, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (payment_id) DO UPDATE SET
            status = EXCLUDED.status,
            metadata = EXCLUDED.metadata
        """
        
        cur.execute(query, (
            donation_data['user_id'],
            donation_data.get('username'),
            donation_data['amount'],
            donation_data['currency'],
            donation_data['payment_system'],
            donation_data['payment_id'],
            donation_data['status'],
            json.dumps(donation_data.get('metadata', {})) if donation_data.get('metadata') else None,
            datetime.now()
        ))
        
        conn.commit()
        logging.info(f"Donation saved: user_id={donation_data['user_id']}, "
                    f"amount={donation_data['amount']}, payment_id={donation_data['payment_id']}")
        return True
        
    except psycopg2.Error as e:
        logging.error(f"Error saving donation: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn and cur:
            close_connection_db(conn, cur)


def update_donation_status(db_params: dict, payment_id: str, status: str) -> bool:
    """
    Обновление статуса доната
    
    Args:
        db_params: Параметры подключения к БД
        payment_id: ID платежа
        status: Новый статус
        
    Returns:
        True если успешно, False если ошибка
    """
    conn = None
    cur = None
    
    try:
        conn, cur = connect_to_db(
            db_params['dbname'],
            db_params['user'],
            db_params['password'],
            db_params['host']
        )
        
        if conn is None or cur is None:
            return False
        
        query = "UPDATE donations SET status = %s WHERE payment_id = %s"
        cur.execute(query, (status, payment_id))
        conn.commit()
        
        if cur.rowcount > 0:
            logging.info(f"Donation status updated: payment_id={payment_id}, status={status}")
            return True
        else:
            logging.warning(f"Donation not found: payment_id={payment_id}")
            return False
            
    except psycopg2.Error as e:
        logging.error(f"Error updating donation status: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn and cur:
            close_connection_db(conn, cur)


def get_user_donations(db_params: dict, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Получение истории донатов пользователя
    
    Args:
        db_params: Параметры подключения к БД
        user_id: ID пользователя
        limit: Максимальное количество записей
        
    Returns:
        Список донатов пользователя
    """
    conn = None
    cur = None
    
    try:
        conn, cur = connect_to_db(
            db_params['dbname'],
            db_params['user'],
            db_params['password'],
            db_params['host']
        )
        
        if conn is None or cur is None:
            return []
        
        query = """
        SELECT amount, currency, payment_system, status, created_at
        FROM donations
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """
        
        cur.execute(query, (user_id, limit))
        donations = cur.fetchall()
        
        # Конвертируем в список словарей
        result = []
        for donation in donations:
            result.append({
                'amount': float(donation['amount']),
                'currency': donation['currency'],
                'payment_system': donation['payment_system'],
                'status': donation['status'],
                'created_at': donation['created_at']
            })
        
        return result
        
    except psycopg2.Error as e:
        logging.error(f"Error getting user donations: {e}")
        return []
    finally:
        if conn and cur:
            close_connection_db(conn, cur)


def get_total_donations(db_params: dict) -> Dict[str, Any]:
    """
    Получение общей статистики по донатам
    
    Args:
        db_params: Параметры подключения к БД
        
    Returns:
        Словарь со статистикой
    """
    conn = None
    cur = None
    
    try:
        conn, cur = connect_to_db(
            db_params['dbname'],
            db_params['user'],
            db_params['password'],
            db_params['host']
        )
        
        if conn is None or cur is None:
            return {
                'total_rub': 0,
                'total_stars': 0,
                'completed_count': 0,
                'total_count': 0,
                'recent': []
            }
        
        # Общая сумма донатов
        query = """
        SELECT 
            COALESCE(SUM(CASE WHEN currency = 'RUB' AND status = 'completed' THEN amount ELSE 0 END), 0) as total_rub,
            COALESCE(SUM(CASE WHEN currency = 'XTR' AND status = 'completed' THEN amount ELSE 0 END), 0) as total_stars,
            COALESCE(COUNT(CASE WHEN status = 'completed' THEN 1 END), 0) as completed_count,
            COALESCE(COUNT(*), 0) as total_count
        FROM donations
        """
        
        cur.execute(query)
        total = cur.fetchone()
        
        # Последние донаты
        query = """
        SELECT username, amount, currency, payment_system, created_at
        FROM donations
        WHERE status = 'completed'
        ORDER BY created_at DESC
        LIMIT 5
        """
        
        cur.execute(query)
        recent = cur.fetchall()
        
        # Форматируем результат
        recent_list = []
        for row in recent:
            recent_list.append({
                'username': row['username'],
                'amount': float(row['amount']),
                'currency': row['currency'],
                'payment_system': row['payment_system'],
                'created_at': row['created_at']
            })
        
        return {
            'total_rub': float(total['total_rub']) if total['total_rub'] else 0,
            'total_stars': float(total['total_stars']) if total['total_stars'] else 0,
            'completed_count': total['completed_count'],
            'total_count': total['total_count'],
            'recent': recent_list
        }
        
    except psycopg2.Error as e:
        logging.error(f"Error getting total donations: {e}")
        return {
            'total_rub': 0,
            'total_stars': 0,
            'completed_count': 0,
            'total_count': 0,
            'recent': []
        }
    finally:
        if conn and cur:
            close_connection_db(conn, cur)


def check_donation_table_exists(db_params: dict) -> bool:
    """
    Проверка существования таблицы donations
    
    Args:
        db_params: Параметры подключения к БД
        
    Returns:
        True если таблица существует, False если нет
    """
    conn = None
    cur = None
    
    try:
        conn, cur = connect_to_db(
            db_params['dbname'],
            db_params['user'],
            db_params['password'],
            db_params['host']
        )
        
        if conn is None or cur is None:
            return False
        
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'donations'
        )
        """
        
        cur.execute(query)
        exists = cur.fetchone()[0]
        return exists
        
    except psycopg2.Error as e:
        logging.error(f"Error checking donations table: {e}")
        return False
    finally:
        if conn and cur:
            close_connection_db(conn, cur)
