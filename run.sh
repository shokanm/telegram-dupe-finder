#!/bin/bash
# Запуск поиска дубликатов
# Двойной клик на этот файл запустит скрипт в Терминале

cd "$(dirname "$0")"

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    osascript -e 'display alert "Python не найден" message "Установите Python 3.11+ с сайта python.org"'
    exit 1
fi

# Устанавливаем зависимости если нужно
python3 -m pip install -r requirements.txt --quiet

# Запускаем
python3 main.py

echo ""
echo "Нажми Enter для закрытия..."
read
