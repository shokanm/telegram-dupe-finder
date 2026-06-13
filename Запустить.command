#!/bin/bash
cd "$(dirname "$0")"

# Проверяем установку
if ! python3 -c "import flask" &>/dev/null; then
    echo "Пакеты не установлены. Сначала запустите 'Установить.command'"
    echo ""
    read -p "Нажмите Enter для закрытия..."
    exit 1
fi

echo "Запускаю DupeFinder..."
echo "Браузер откроется автоматически."
echo ""
echo "Чтобы остановить программу — закройте это окно."
echo ""

python3 app.py
