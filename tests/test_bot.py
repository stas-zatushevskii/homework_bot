from http import HTTPStatus

import requests
import telegram
import utils
import os


class MockResponseGET:

    def __init__(self, url, params=None, random_timestamp=None,
                 current_timestamp=None, http_status=HTTPStatus.OK, **kwargs):
        assert (
            url.startswith(
                'https://practicum.yandex.ru/api/user_api/homework_statuses'
            )
        ), (
            'Проверьте, что вы делаете запрос на правильный '
            'ресурс API для запроса статуса домашней работы'
        )
        assert 'headers' in kwargs, (
            'Проверьте, что вы передали заголовки `headers` для запроса '
            'статуса домашней работы'
        )
        assert 'Authorization' in kwargs['headers'], (
            'Проверьте, что в параметрах `headers` для запроса статуса '
            'домашней работы добавили Authorization'
        )
        assert kwargs['headers']['Authorization'].startswith('OAuth '), (
            'Проверьте,что в параметрах `headers` для запроса статуса '
            'домашней работы Authorization начинается с OAuth'
        )
        assert params is not None, (
            'Проверьте, что передали параметры `params` для запроса '
            'статуса домашней работы'
        )
        assert 'from_date' in params, (
            'Проверьте, что в параметрах `params` для запроса статуса '
            'домашней работы `from_date`'
        )
        assert params['from_date'] == current_timestamp, (
            'Проверьте, что в параметрах `params` для запроса статуса '
            'домашней работы `from_date` передаете timestamp'
        )
        self.random_timestamp = random_timestamp
        self.status_code = http_status

    def json(self):
        data = {
            "homeworks": [],
            "current_date": self.random_timestamp
        }
        return data


class MockTelegramBot:

    def __init__(self, token=None, random_timestamp=None, **kwargs):
        assert token is not None, (
            'Проверьте, что вы передали токен бота Telegram'
        )
        self.random_timestamp = random_timestamp

    def send_message(self, chat_id=None, text=None, **kwargs):
        assert chat_id is not None, (
            'Проверьте, что вы передали chat_id= при отправке '
            'сообщения ботом Telegram'
        )
        assert text is not None, (
            'Проверьте, что вы передали text= при отправке '
            'сообщения ботом Telegram'
        )
        return self.random_timestamp


class TestHomework:
    env_vars = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    for v in env_vars:
        try:
            os.environ.pop(v)
        except KeyError:
            pass
    try:
        import homework_bot.homework as homework
    except KeyError as e:
        for arg in e.args:
            if arg in env_vars:
                assert False, (
                    'Убедитесь, что при запуске бота, проверяете наличие '
                    'переменных окружения, и при их отсутствии происходит '
                    'выход из программы `SystemExit`\n'
                    f'{repr(e)}'
                )
            else:
                raise
    except SystemExit:
        for v in env_vars:
            os.environ[v] = ''

    def test_logger(self, monkeypatch, random_timestamp):
        def mock_telegram_bot(*args, **kwargs):
            return MockTelegramBot(*args, random_timestamp=random_timestamp, **kwargs)

        monkeypatch.setattr(telegram, "Bot", mock_telegram_bot)

        import homework_bot.homework as homework

        assert hasattr(homework, 'logging'), (
            'Убедитесь, что настроили логирование для вашего бота'
        )

    def test_send_message(self, monkeypatch, random_timestamp):
        def mock_telegram_bot(*args, **kwargs):
            return MockTelegramBot(*args, random_timestamp=random_timestamp, **kwargs)

        monkeypatch.setattr(telegram, "Bot", mock_telegram_bot)

        import homework_bot.homework as homework
        utils.check_function(homework, 'send_message', 2)

    def test_get_api_answers(self, monkeypatch, random_timestamp,
                             current_timestamp, api_url):
        def mock_response_get(*args, **kwargs):
            return MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp, **kwargs
            )

        monkeypatch.setattr(requests, 'get', mock_response_get)

        import homework_bot.homework as homework

        func_name = 'get_api_answer'
        utils.check_function(homework, func_name, 2)

        result = homework.get_api_answer(api_url, current_timestamp)
        assert type(result) == dict, (
            f'Проверьте, что из функции `{func_name}` '
            'возвращается словарь'
        )
        keys_to_check = ['homeworks', 'current_date']
        for key in keys_to_check:
            assert key in result, (
                f'Проверьте, что функция `{func_name}` '
                f'возвращает словарь, содержащий ключ `{key}`'
            )
        assert type(result['current_date']) == int, (
            f'Проверьте, что функция `{func_name}` '
            'в ответе API возвращает значение '
            'ключа `current_date` типа `int`'
        )
        assert result['current_date'] == random_timestamp, (
            f'Проверьте, что функция `{func_name}` '
            'в ответе API возвращает корректное значение '
            'ключа `current_date`'
        )

    def test_get_500_api_answer(self, monkeypatch, random_timestamp,
                                current_timestamp, api_url):
        def mock_500_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                http_status=HTTPStatus.INTERNAL_SERVER_ERROR, **kwargs
            )

            def json_invalid():
                data = {
                }
                return data

            response.json = json_invalid
            return response

        monkeypatch.setattr(requests, 'get', mock_500_response_get)

        import homework_bot.homework as homework

        func_name = 'get_api_answer'
        try:
            homework.get_api_answer(api_url, current_timestamp)
        except:
            return
        assert False, (
            f'Убедитесь, что в функции `{func_name}` обрабатываете ситуацию, '
            'когда API возвращает код, отличный от 200'
        )

    def test_parse_status(self, random_timestamp):
        test_data = {
            "id": 123,
            "status": "approved",
            "homework_name": str(random_timestamp),
            "reviewer_comment": "Всё нравится",
            "date_updated": "2020-02-13T14:40:57Z",
            "lesson_name": "Итоговый проект"
        }

        import homework_bot.homework as homework

        func_name = 'parse_status'

        utils.check_function(homework, func_name, 1)

        result = homework.parse_status(test_data)
        assert result.startswith(
            f'Изменился статус проверки работы "{random_timestamp}"'
        ), (
            'Проверьте, что возвращаете название домашней работы в возврате '
            f'функции `{func_name}`'
        )
        assert result.endswith(
            'Работа проверена: ревьюеру всё понравилось. Ура!'
        ), (
            'Проверьте, что возвращаете правильный вердикт для статуса '
            f'`approved` в возврате функции `{func_name}`'
        )

        test_data['status'] = 'rejected'
        result = homework.parse_status(test_data)
        assert result.startswith(
            f'Изменился статус проверки работы "{random_timestamp}"'
        ), (
            'Проверьте, что возвращаете название домашней работы '
            'в возврате функции parse_status()'
        )
        assert result.endswith(
            'Работа проверена, в ней нашлись ошибки.'
        ), (
            'Проверьте, что возвращаете правильный вердикт для статуса '
            'rejected в возврате функции parse_status()'
        )

    def test_check_response(self, monkeypatch, random_timestamp,
                            current_timestamp, api_url):
        def mock_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                **kwargs
            )

            def valid_response_json():
                data = {
                    "homeworks": [
                        {
                            'homework_name': 'hw123',
                            'status': 'approved'
                        }
                    ],
                    "current_date": random_timestamp
                }
                return data

            response.json = valid_response_json
            return response

        monkeypatch.setattr(requests, 'get', mock_response_get)

        import homework_bot.homework as homework

        func_name = 'check_response'
        response = homework.get_api_answer(api_url, current_timestamp)
        status = homework.check_response(response)
        assert status, (
            f'Убедитесь, что функция `{func_name} '
            'правильно работает '
            'при корректном ответе от API'
        )

    def test_check_response_unknown_status(self, monkeypatch, random_timestamp,
                                           current_timestamp, api_url):
        def mock_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                **kwargs
            )

            def valid_response_json():
                data = {
                    "homeworks": [
                        {
                            'homework_name': 'hw123',
                            'status': 'unknown'
                        }
                    ],
                    "current_date": random_timestamp
                }
                return data

            response.json = valid_response_json
            return response

        monkeypatch.setattr(requests, 'get', mock_response_get)

        import homework_bot.homework as homework

        func_name = 'check_response'
        response = homework.get_api_answer(api_url, current_timestamp)
        try:
            homework.check_response(response)
        except:
            return
        assert False, (
            f'Убедитесь, что функция `{func_name} правильно работает '
            'при недокументированном статусе домашней работы в ответе от API'
        )

    def test_check_response_no_homeworks(self, monkeypatch, random_timestamp,
                                         current_timestamp, api_url):
        def mock_no_homeworks_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                **kwargs
            )

            def json_invalid():
                data = {
                    "current_date": random_timestamp
                }
                return data

            response.json = json_invalid
            return response

        monkeypatch.setattr(requests, 'get', mock_no_homeworks_response_get)

        import homework_bot.homework as homework

        func_name = 'check_response'
        result = homework.get_api_answer(api_url, current_timestamp)
        try:
            homework.check_response(result)
        except:
            return
        assert False, (
            f'Убедитесь, что в функции `{func_name} '
            'обрабатываете ситуацию, когда ответ от API '
            'не содержит ключа `homeworks`, и выбрасываете ошибку'
        )

    def test_check_response_empty(self, monkeypatch, random_timestamp,
                                  current_timestamp, api_url):
        def mock_empty_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                **kwargs
            )

            def json_invalid():
                data = {
                }
                return data

            response.json = json_invalid
            return response

        monkeypatch.setattr(requests, 'get', mock_empty_response_get)

        import homework_bot.homework as homework

        func_name = 'check_response'
        result = homework.get_api_answer(api_url, current_timestamp)
        try:
            homework.check_response(result)
        except:
            return
        assert False, (
            f'Убедитесь, что в функции `{func_name} '
            'обрабатываете ситуацию, когда ответ от API '
            'содержит пустой словарь`, и выбрасываете ошибку'
        )

    def test_api_response_timeout(self, monkeypatch, random_timestamp,
                                  current_timestamp, api_url):
        def mock_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                http_status=HTTPStatus.REQUEST_TIMEOUT, **kwargs
            )
            return response

        monkeypatch.setattr(requests, 'get', mock_response_get)

        import homework_bot.homework as homework

        func_name = 'check_response'
        try:
            homework.get_api_answer(api_url, current_timestamp)
        except:
            return
        assert False, (
            f'Убедитесь, что в функции `{func_name}` обрабатываете ситуацию, '
            'когда API возвращает код, отличный от 200'
        )
