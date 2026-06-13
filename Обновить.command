#!/bin/bash
cd "$(dirname "$0")"

REPO_URL="https://github.com/shokanm/telegram-dupe-finder.git"
BRANCH="main"

echo "================================================"
echo "  Обновление DupeFinder"
echo "================================================"
echo ""

# ── Проверяем git ─────────────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
    echo "Git не найден. Устанавливаю Xcode Command Line Tools..."
    echo ""
    xcode-select --install 2>/dev/null
    echo ""
    echo "После завершения установки запустите этот файл снова."
    read -p "Нажмите Enter для закрытия..."
    exit 1
fi

# ── Первый запуск: подключаем к репозиторию ──────────────────────────────────
if [ ! -d ".git" ]; then
    echo "Первый запуск — подключаю к репозиторию..."
    git init -q
    git remote add origin "$REPO_URL"
    echo ""
fi

# ── Скачиваем изменения ───────────────────────────────────────────────────────
echo "Проверяю обновления..."
git fetch origin "$BRANCH" -q 2>&1

if [ $? -ne 0 ]; then
    echo ""
    echo "ОШИБКА: Не удалось подключиться к серверу."
    echo "Проверьте подключение к интернету и попробуйте снова."
    read -p "Нажмите Enter для закрытия..."
    exit 1
fi

LOCAL=$(git rev-parse HEAD 2>/dev/null || echo "none")
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    echo ""
    echo "Уже установлена последняя версия."
else
    echo "Устанавливаю обновление..."
    git checkout -f -B "$BRANCH" "origin/$BRANCH" -q
    echo "Обновление установлено!"
fi

# ── Обновляем зависимости (на случай новых пакетов) ──────────────────────────
echo "Проверяю зависимости..."
python3 -m pip install -r requirements.txt --quiet

echo ""
echo "================================================"
echo "  Готово!"
echo ""
echo "  Запустите 'Запустить.command' для старта."
echo "================================================"
echo ""
read -p "Нажмите Enter для закрытия..."
