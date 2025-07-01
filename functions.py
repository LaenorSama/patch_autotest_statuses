import requests
import os
import re
import json
from collections import defaultdict
# библиотека для загрузки данных из env
from dotenv import load_dotenv

# заполняем словарь своих статусов и их ID
STATUSES = {"Черновик": -1,
            "Проверка": 37,
            "Устранение замечаний": 38,
            "Активный": -3
            }
# заполняем словарь своих воркфлоу и их ID
WORKFLOW = {"Advanced Automated": 35}
WORKFLOW_ID = 35
# заполняем словарь соответствий результатов и статусов по их ID
# сперва хотел указывать по ключам из словаря, но передумал
RESULT_STATUSES = {"passed": -3,
                   "failed": 38,
                   "broken": 37,
                   "skipped": -1,
                   "unknown": -1
                   }

# создаем API URL для дальнейших запросов
def generate_api_url(instance_name):
    """Генерирует API URL для инстанса."""
    return f"https://{instance_name}/api/"

# создаем URL для нашего инстанса
def generate_url(instance_name):
    """Генерирует API URL для инстанса."""
    return f"https://{instance_name}/"

# функция для получения bearer-токена нужного инстанса для токена администратора
def get_bearer_token(testops_api_url, testops_token):
    # URL для получения токена
    url = f"{testops_api_url}uaa/oauth/token"

    # Данные для запроса (в формате x-www-form-urlencoded)
    data = {
        "grant_type": "apitoken",
        "scope": "openid",
        "token": testops_token
    }

    # Заголовки
    headers = {
        "Accept": "application/json"
    }

    # Отправляем POST-запрос
    response = requests.post(url, data=data, headers=headers)

    # Проверяем успешность запроса
    if response.status_code == 200:
        try:
            token = response.json().get("access_token")
            if token:
                print("Bearer-токен получен")
                return token
            else:
                print("Ответ не содержит access_token:", response.json())
        except requests.exceptions.JSONDecodeError:
            print("Ошибка парсинга JSON:", response.text)
    else:
        print("Ошибка получения токена:", response.status_code, response.text)

# получаем ID проекта
def get_project_id(instance_api_url, project_name, bearer_token):
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"  # Для корректной обработки JSON
    }
    # Получаем список проектов
    response = requests.get(f"{instance_api_url}project?page=0&size=100&sort=name%2CASC", headers=headers)
    # Проверка успешности запроса
    if response.status_code == 200:
        projects = response.json()
        # Ищем проект по названию
        project_id = None
        for project in projects.get('content', []):
            if project['name'] == project_name:
                project_id = project['id']
        # проверка все получилось или нет
        if project_id:
            print(f"ID проекта '{project_name}': {project_id}")
        else:
            print(f"Проект с названием '{project_name}' не найден.")
    else:
        print(f"Ошибка при запросе: {response.status_code}, {response.text}")
    return project_id

# получаем ID запуска
def get_launch_id(LAUNCH_URL):
    # Используем регулярное выражение для поиска чисел в конце строки, это launch_id
    match = re.search(r'(\d+)$', LAUNCH_URL)
    if match:
        print(f"Launch ID: {match.group(1)}")
        return match.group(1)  # Возвращаем найденный launch_id
    else:
        print("❌ Не удалось извлечь launch_id")
        return None

# получаем результаты автотестов из запуска
def get_test_results(instance_api_url, launch_id, bearer_token):
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"  # Для корректной обработки JSON
    }
    # Получаем список проектов
    response = requests.get(f"{instance_api_url}testresult?launchId={launch_id}&page=0&size=100&sort=name%2CASC", headers=headers)
    # Проверка успешности запроса
    if response.status_code == 200:
        test_results = response.json()
    else: print(f"Ошибка при запросе: {response.status_code}, {response.text}")

    result = defaultdict(list)

    for test in test_results.get("content", []):
        if not test.get("manual", False):
            status = test.get("status")
            test_case_id = test.get("testCaseId")
            if status and test_case_id is not None:
                result[status].append(test_case_id)

    # Преобразуем defaultdict в обычный словарь
    output = dict(result)

    # Выводим результат
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return output

# инициируем смену статусов в соответствии с RESULT_STATUSES
def change_statuses(instance_api_url, project_id, bearer_token, test_results, result_statuses):
    endpoint = f"{instance_api_url}v2/test-case/bulk/status/set"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    for status, test_case_ids in test_results.items():
        if not test_case_ids:
            continue

        status_id = result_statuses.get(status, -1)
        # формируем тело запроса
        payload = {
            "selection": {
                "projectId": project_id,
                "testCasesInclude": test_case_ids
            },
            "statusId": status_id,
            "workflowId": WORKFLOW_ID # тут тоже сперва хотел указывать по ключам из словаря, но передумал
        }
        print(f"POST {endpoint} with payload:\n{payload}")
        response = requests.post(endpoint, headers=headers, json=payload)
        print(f"[{status.upper()}] Sent {len(test_case_ids)} IDs → Status {response.status_code}")