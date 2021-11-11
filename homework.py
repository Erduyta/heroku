import logging
import os
import time

import requests
from dotenv import load_dotenv
from telegram import Bot
from flask import Flask

app = Flask(__name__)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('TOKEN_PRACTICUM')
TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGRAM')
CHAT_ID = os.getenv('CHAT_ID')


RETRY_TIME = 300
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}

error_messages = []
global last_msg
last_msg = ''
print('start')
logging.basicConfig(level=logging.DEBUG)
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
logging.getLogger('').addHandler(console)


def check_tokens():
    """Проверяет доступность переменных окружения,
    которые необходимы для работы программы
    """
    if PRACTICUM_TOKEN is None:
        logging.critical(
            'Отсутствует обязательная переменная окружения: PRACTICUM_TOKEN')
        return False
    if TELEGRAM_TOKEN is None:
        logging.critical(
            'Отсутствует обязательная переменная окружения: TELEGRAM_TOKEN')
        return False
    if CHAT_ID is None:
        logging.critical(
            'Отсутствует обязательная переменная окружения: CHAT_ID')
        return False
    return True


def send_message(bot, message):
    """Oтправляет сообщение в Telegram чат
    """
    try:
        bot.send_message(
            chat_id=CHAT_ID,
            text=message
        )
        logging.info(f'Бот отправил сообщение "{message}"')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения хозяину: {error}')


def get_api_answer(url, current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса
    """
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    response = requests.get(url, headers=headers, params=payload)
    if response.status_code == 200:
        return response.json()
    raise Exception(
        'Ошибка при запросе к основному API,'
        f'status_code: {response.status_code}')


def parse_status(homework):
    """Извлекает статус конкретной домашней работы
    """
    verdict = HOMEWORK_STATUSES[homework.get('status')]
    homework_name = homework.get('homework_name')
    logging.info(
        f'Изменился статус проверки работы "{homework_name}". {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_response(response):
    """Проверяет ответ API на корректность
    """
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise Exception('Ответ API не соответствует ожидаемому: None')
    if type(homeworks) != list:
        raise Exception('Ответ API не соответствует ожидаемому: not list')
    if len(homeworks) > 0:
        homework = homeworks[0]
        if homework.get('status') is None:
            raise Exception('Нет статуса домашней работы')
        if homework.get('status') not in HOMEWORK_STATUSES.keys():
            raise Exception('Неожиданный статус домашней работы')
        if homework.get('homework_name') is None:
            raise Exception('Нет имени домашней работы')
        return homework
    logging.debug('Нет домашних работ в ответе API')
    return None


def main():
    """Main func
    """
    global last_msg
    logging.info('Start!')
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - 3600 * 5
    if not check_tokens():
        print('Программа принудительно остановлена.')
        quit()
    while True:
        try:
            api_answer = get_api_answer(ENDPOINT, current_timestamp)
            homework = check_response(api_answer)
            if homework is not None:
                msg = parse_status(homework)
                if last_msg != msg:
                    last_msg = msg
                    send_message(bot, msg)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if message not in error_messages:
                error_messages.append(message)
                send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    main()
