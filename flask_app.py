from flask import Flask, request, jsonify
import uuid
import os
from functions import *
import json
# библиотека для загрузки данных из env
from dotenv import load_dotenv

app = Flask(__name__)
# url: http://62.16.40.27:5000/webhook
# папка куда сохраняем все полученные вебхуки
WEBHOOKS_DIR = "webhooks"

@app.route("/webhook", methods=["POST"])
def webhook():
    # укажите свой инстанс
    INSTANCE_NAME = "demo.qatools.cloud"
    # получаем URL инстанса
    INSTANCE_URL = generate_url(INSTANCE_NAME)
    print(f"Инстанс URL: {INSTANCE_URL}")
    # получаем API URL инстанса
    INSTANCE_API_URL= generate_api_url(INSTANCE_NAME)
    print(f"Инстанс URL: {INSTANCE_API_URL}")
    # Загружаем .env файл
    load_dotenv()
    # Получаем токен из .env файла
    TESTOPS_TOKEN = os.getenv("TESTOPS_TOKEN")
    # Генерируем bearer-токен
    BEARER_TOKEN = get_bearer_token(INSTANCE_API_URL, TESTOPS_TOKEN)

    # Обрабатываем вебхук и сохраняем его в файл
    data = request.json  # Получаем JSON-данные из запроса

    if not data:
        return jsonify({"error": "No data received"}), 400

    # Сохраняем в файл с уникальным именем
    filename = os.path.join(WEBHOOKS_DIR, f"webhook_{uuid.uuid4()}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Вебхук сохранён: {filename}")  # Логируем в консоли

    # парсим полученный вебхук
    LAUNCH_NAME = data.get("launch_name")
    print(f"Launch_name: '{LAUNCH_NAME}'")
    LAUNCH_URL = data.get("launch_url")
    print(f"Launch_url: '{LAUNCH_URL}'")
    PROJECT_NAME = data.get("project_name")
    print(f"Project_name: '{PROJECT_NAME}'")
    PROJECT_ID = get_project_id(INSTANCE_API_URL, PROJECT_NAME, BEARER_TOKEN)
    LAUNCH_ID = get_launch_id(LAUNCH_URL)

    # получаем результаты автотестов и сразу группируем
    TEST_RESULTS = get_test_results(INSTANCE_API_URL, LAUNCH_ID, BEARER_TOKEN)

    # инициируем обновление статусов
    change_statuses(INSTANCE_API_URL, PROJECT_ID, BEARER_TOKEN, TEST_RESULTS, RESULT_STATUSES)
    return jsonify({"status": "ok", "message": "Webhook received"}), 200

def start_flask_app():
    # Запускаем Flask-приложение
    app.run(port=5000, debug=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


