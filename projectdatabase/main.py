import bs4
import sqlite3
import psycopg2
import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
import asyncio
import aiohttp
import logging
import shutil
import os
import json
from dotenv import load_dotenv
import boto3
from botocore.config import Config



load_dotenv()
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("app.log", encoding="utf-8"), logging.StreamHandler()]
)

# URL RSS
url = os.environ['URL']

# Функция для удаления HTML-тегов
def remove_html_tags(text):
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text()

# Функция для фильтрации текста
def clean_text(text):
    if not text:
        return ""
    text = remove_html_tags(text)  # Удаляем HTML-теги
    text = re.sub(r'\s+', ' ', text)  # Удаляем лишние пробелы
    text = re.sub(r'\.(?!\s|$)', '. ', text)  # Добавляем пробел после точки, если его нет
    return text.strip()  # Удаляем пробелы в начале и конце

# Асинхронное извлечение текстов JSON-LD
async def fetch_ldjson(session, link):
    try:
        async with session.get(link) as response:
            html_code = await response.text()
            soup = BeautifulSoup(html_code, 'html.parser')
            script_tags = soup.find_all('script', {"type": "application/ld+json"})
            text_list = []
            for script_tag in script_tags:
                script_text = script_tag.get_text()
                text_list.extend(re.findall(r'"articleBody":\s*"(.*?)"', script_text))
            logging.info(f"Данные успешно получены с {link}")
            return text_list
    except Exception as e:
        logging.error(f"Ошибка при получении данных с {link}: {e}")
        return []

# Асинхронная обработка всех ссылок
async def extract_texts_from_links(links):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_ldjson(session, link) for link in links]
        results = await asyncio.gather(*tasks)
    return [item for sublist in results for item in sublist]

# Функция для загрузки изображений
def download_image(image_url, save_path):
    try:
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            logging.info(f"Изображение сохранено: {save_path}")
            return save_path
        else:
            logging.error(f"Ошибка при загрузке изображения: {image_url}")
            return None
    except Exception as e:
        logging.error(f"Ошибка при загрузке изображения: {image_url}, {e}")
        return None

# Основной блок извлечения данных из RSS
logging.info("Получение данных из RSS")
url_code = requests.get(url)
soup = bs4.BeautifulSoup(url_code.text, features='xml')

# Сбор данных из RSS
currencies = []
guid_id = soup.find_all('guid')
title = soup.find_all('title')[2:]
link = soup.find_all('link')[2:]
pdalink = soup.find_all('pdalink')
pubdate = soup.find_all('pubDate')
description = soup.find_all('description')[1:]
category = soup.find_all('category')
author = soup.find_all('author')
enclosures = soup.find_all('enclosure')

# Создаем папку для изображений внутри проекта
image_folder = './project/images'
os.makedirs(image_folder, exist_ok=True)

logging.info("Обработка данных RSS")
for i in range(len(guid_id)):
    guid = guid_id[i].get_text()
    image_url = enclosures[i].get('url') if enclosures[i] else None
    image_path = None

    # Скачиваем изображение
    if image_url:
        filename = f"{guid}.jpg"
        save_path = os.path.join(image_folder, filename)
        image_path = download_image(image_url, save_path)

    row = [
        guid,
        clean_text(title[i].get_text()),
        link[i].get_text().strip(),
        pdalink[i].get_text().strip(),
        pubdate[i].get_text().strip(),
        clean_text(description[i].get_text()),
        clean_text(category[i].get_text()),
        author[i].get_text().strip(),
        image_path,  
        ''  # Заглушка для текста (texts)
    ]
    currencies.append(row)

# Асинхронное извлечение текстов из ссылок
logging.info("Получение дополнительных данных из ссылок")
cleaned_links = [link.get_text().strip() for link in pdalink]
all_texts = asyncio.run(extract_texts_from_links(cleaned_links))

# Добавляем тексты к данным
logging.info("Объединение данных")
for i in range(len(currencies)):
    currencies[i][-1] = clean_text(all_texts[i]) if i < len(all_texts) else ''  # Обновляем поле texts

# Конвертируем данные в DataFrame
db = pd.DataFrame(currencies, columns=[
    'guid_id', 'title', 'link', 'pdalink', 'pubdate', 'description', 'category', 'author', 'image_path', 'texts'
])

# Создаём JSON
db.to_json('data.json', orient='records', indent=None)

# Читаем JSON
with open('data.json', 'r') as f:
    data = json.load(f)


# Подключение к PostgreSQL
try:
    logging.info("Подключение к базе данных PostgreSQL")
    pg_conn = psycopg2.connect(
        dbname=os.environ['DBNAME'],
        user=os.environ['USER'],
        password=os.environ['PASSWORD'],
        host=os.environ['HOST'],
        port=os.environ['PORT']
    )
    pg_cur = pg_conn.cursor()

    # Создание таблицы PostgreSQL
    pg_cur.execute('''
    CREATE TABLE IF NOT EXISTS mytable (
        guid_id TEXT PRIMARY KEY,
        title TEXT,
        link TEXT,
        pdalink TEXT,
        pubdate TEXT,
        description TEXT,
        category TEXT,
        author TEXT,
        image_path TEXT,
        texts TEXT
    );
    ''')

    # Вставка данных в PostgreSQL
    for _, row in db.iterrows():
        pg_cur.execute('''
        INSERT INTO news (id, title, link, pdalink, pubdate, description, category, author, image_path, texts)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING;
        ''', tuple(row))
    pg_conn.commit()

except psycopg2.Error as e:
    logging.error(f"Ошибка при работе с PostgreSQL: {e}")
finally:
    pg_cur.close()
    pg_conn.close()


def upload_images_to_s3(folder_path, bucket_name, s3_url, access_key, secret_key):
    # Подключение к S3 совместимому хранилищу
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{s3_url}",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(s3={"addressing_style": "path"})
    )
    
    # Перебираем файлы в папке
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            object_name = os.path.relpath(file_path, folder_path)
            
            # Загружаем файл в S3
            with open(file_path, "rb") as data:
                s3.upload_fileobj(data, bucket_name, object_name)
                print(f"Загружен: {object_name}")
    
    print("Все файлы загружены!")

# Данные для S3
FOLDER_PATH = os.environ["FOLDER_PATHENV"]
BUCKET_NAME = os.environ["BUCKET_NAMEENV"]
S3_URL = os.environ["S3_URLENV"]
ACCESS_KEY = os.environ["ACCESS_KEYENV"]
SECRET_KEY = os.environ["SECRET_KEYENV"]
FOLDER_PATH_TWO = os.environ["FOLDER_PATHAIGEN"]
# Запуск загрузки
upload_images_to_s3(FOLDER_PATH, BUCKET_NAME, S3_URL, ACCESS_KEY, SECRET_KEY)




def upload_aigenimages_to_s3(folder_path, bucket_name, s3_url, access_key, secret_key):
    # Подключение к S3 совместимому хранилищу
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{s3_url}",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(s3={"addressing_style": "path"})
    )
    
    # Перебираем файлы в папке
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Устанавливаем путь в S3: добавляем папку "aigenimage/"
            object_name = f"aigenimage/{os.path.relpath(file_path, folder_path)}"

            try:
                with open(file_path, "rb") as data:
                    s3.upload_fileobj(data, bucket_name, object_name)
                print(f"Загружен: {object_name}")
            except Exception as e:
                print(f"Ошибка загрузки {file_path}: {e}")

    print("Все файлы загружены!")

# Данные для S3
FOLDER_PATH = os.getenv("FOLDER_PATHAIGEN") 
BUCKET_NAME = os.getenv("BUCKET_NAMEENV")
S3_URL = os.getenv("S3_URLENV")
ACCESS_KEY = os.getenv("ACCESS_KEYENV")
SECRET_KEY = os.getenv("SECRET_KEYENV")

# Проверяем, заданы ли все переменные
if not all([BUCKET_NAME, S3_URL, ACCESS_KEY, SECRET_KEY]):
    print("Ошибка: Не все переменные окружения заданы!")
else:
    upload_aigenimages_to_s3(FOLDER_PATH, BUCKET_NAME, S3_URL, ACCESS_KEY, SECRET_KEY)

    