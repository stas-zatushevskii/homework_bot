import logging
import os
import time

from dotenv import load_dotenv
from telegram import Bot
import requests

load_dotenv()

PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
URL = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

bot = Bot(token=TELEGRAM_TOKEN)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename=os.path.expanduser('~/main.log'),
        filemode='w',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',

    )


REJECTED = 'К сожалению, в работе нашлись ошибки.'
REVIEWING = 'Работа взята в ревью'
PPROVED = 'Ревьюеру всё понравилось, работа зачтена!'
ANSWER = (
    'У вас проверили работу "{name}" !\n\n{verdict}')
UNEXPECTED_RESPONSE = 'Неожиданный статус в ответе сервера: {status_name}'
ERROR = 'Сервер сообщил об отказ'
HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
MAIN_ERROR = 'что-то не получилось {error}'
KEY = (
    'Яндекс дал сбой : неожиданный ключ: {homework_json_key},',
    'headers: {headers}, from_date: {payload}, URL: {url}')
CONECT_ERROR = ('Ошибка соединения, :{payload},'
                + '{headers}, ошибка : {error}, {url}')

STATUSES = {
    'rejected': REJECTED,
    'reviewing': REVIEWING,
    'approved': PPROVED
}


def parse_homework_status(homework):
    status = homework['status']
    if status in STATUSES:
        verdict = STATUSES[status]
    else:
        raise ValueError(
            UNEXPECTED_RESPONSE.format(status_name=STATUSES[status]))
    return ANSWER.format(
        name=homework['homework_name'], verdict=verdict)


def get_homeworks(current_timestamp):
    payload = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(URL, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        raise ConnectionError(
            CONECT_ERROR.format(
                payload=payload, headers=HEADERS, error=error, url=URL))
    # на случай если ответ от яндекса не утешающий
    homework_json = homework_statuses.json()
    for key in ('code', 'error'):
        if key in homework_json:
            raise RuntimeError(
                KEY.format(
                    homework_json_key=homework_json[key],
                    headers=HEADERS,
                    payload=payload,
                    url=URL)
            )
    return homework_json


def send_message(message):
    return bot.send_message(message)


def main():
    current_timestamp = int(time.time())  # Начальное значение timestamp

    while True:
        try:
            homework_statuses = get_homeworks(current_timestamp)
            current_timestamp = homework_statuses.get(
                "current_date", current_timestamp)
            homework = homework_statuses['homeworks']
            message = parse_homework_status(homework[0])
            send_message(message)

            time.sleep(5 * 60)  # Опрашивать раз в пять минут

        except Exception as error:
            main_error = MAIN_ERROR.format(error=error)
            print(main_error)
            logging.error(main_error, exc_info=True)
            time.sleep(13 * 60)


if __name__ == '__main__':
    main()
