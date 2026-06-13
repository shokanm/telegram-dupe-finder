#!/bin/bash
cd "$(dirname "$0")"

echo "================================================"
echo "  Установка DupeFinder"
echo "================================================"
echo ""

# ── Проверяем Python ─────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "Python не найден. Скачиваю установщик..."
    echo ""

    PKG="/tmp/python_installer.pkg"
    curl -L --progress-bar \
        "https://www.python.org/ftp/python/3.12.4/python-3.12.4-macos11.pkg" \
        -o "$PKG"

    echo ""
    echo "Открываю установщик Python..."
    echo "Пройдите установку (нажимайте Продолжить → Установить)."
    echo "Когда завершите, вернитесь в это окно."
    echo ""
    open "$PKG"

    read -p "Нажмите Enter после завершения установки Python..."
    echo ""

    # Обновляем PATH после установки
    export PATH="/usr/local/bin:/usr/bin:$PATH"
    hash -r

    if ! command -v python3 &>/dev/null; then
        echo "ОШИБКА: Python всё ещё не найден."
        echo "Попробуйте перезапустить этот файл после установки."
        read -p "Нажмите Enter для закрытия..."
        exit 1
    fi
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python $PYTHON_VERSION найден."
echo ""

# ── Устанавливаем зависимости ─────────────────────────────────────────────────
echo "Устанавливаю необходимые пакеты (может занять 1-2 минуты)..."
python3 -m pip install -r requirements.txt --quiet

if [ $? -ne 0 ]; then
    echo ""
    echo "ОШИБКА при установке пакетов."
    echo "Попробуйте запустить этот файл снова."
    read -p "Нажмите Enter для закрытия..."
    exit 1
fi

# ── Создаём нужные папки ──────────────────────────────────────────────────────
mkdir -p data/thumbs data/reports

echo ""
echo "================================================"
echo "  Установка завершена успешно!"
echo ""
echo "  Теперь дважды кликните 'Запустить.command'"
echo "================================================"
echo ""
read -p "Нажмите Enter для закрытия..."
