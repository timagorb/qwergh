FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем необходимые системные зависимости
RUN apt-get update && apt-get install -y \
    libxml2 \
    libxslt1-dev \
    cron \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Создаём символическую ссылку для python3
RUN ln -sf /usr/local/bin/python3 /usr/bin/python3

# Копируем зависимости и устанавливаем их
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы в контейнер
COPY . .

# Добавляем cron задание
RUN echo "0 */3 * * * python3 /app/main.py >> /app/app.log 2>&1" > /etc/cron.d/rss_cron
RUN chmod 0644 /etc/cron.d/rss_cron
RUN crontab /etc/cron.d/rss_cron

# Команда запуска cron
CMD ["cron", "-f"]
