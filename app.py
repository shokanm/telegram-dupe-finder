"""
Веб-интерфейс для поиска дубликатов фото.
Запуск: python app.py
"""
import asyncio
import queue
import threading
import webbrowser
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat

import config
from db import init_db, get_all_photos, get_photos_by_groups, update_group_name, clear_all
from hasher import find_exact_duplicates, find_similar_duplicates
from reporter import generate_report
from whatsapp_loader import load_whatsapp_export

app = Flask(__name__)

# ── HTML-интерфейс ────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DupeFinder</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --blue:#0071e3;--blue-lt:#e8f1fb;--green:#28a745;--green-lt:#eaf7ee;
  --amber:#d97706;--amber-lt:#fffbeb;--red:#dc2626;--red-lt:#fff1f0;
  --text:#1d1d1f;--muted:#6e6e73;--border:#e5e5ea;--bg:#f5f5f7;--white:#fff;
}
body{font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue',sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:40px 24px;-webkit-font-smoothing:antialiased}
.card{background:var(--white);border:1px solid var(--border);border-radius:18px;
  padding:40px 44px;width:100%;max-width:560px;
  box-shadow:0 4px 24px rgba(0,0,0,.06)}
.logo{display:flex;align-items:center;gap:10px;margin-bottom:28px}
.logo svg{flex-shrink:0}
.logo-text{font-size:1.1rem;font-weight:700;letter-spacing:-.02em}
h1{font-size:1.5rem;font-weight:700;letter-spacing:-.03em;margin-bottom:6px}
.subtitle{font-size:.88rem;color:var(--muted);margin-bottom:32px}
.field{margin-bottom:20px}
.label{font-size:.78rem;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px}
.source-tabs{display:flex;gap:6px}
.tab{flex:1;padding:9px;border:1.5px solid var(--border);border-radius:10px;
  font-size:.82rem;font-weight:500;text-align:center;cursor:pointer;
  background:var(--white);color:var(--muted);transition:all .15s}
.tab:hover{border-color:var(--blue);color:var(--blue)}
.tab.active{background:var(--blue-lt);border-color:var(--blue);color:var(--blue);font-weight:600}
.folder-row{display:flex;gap:8px;align-items:center}
.folder-path{flex:1;background:var(--bg);border:1.5px solid var(--border);
  border-radius:10px;padding:10px 14px;font-size:.82rem;color:var(--muted);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.folder-path.selected{color:var(--text)}
.btn-pick{padding:10px 16px;background:var(--white);border:1.5px solid var(--border);
  border-radius:10px;font-size:.82rem;font-weight:500;cursor:pointer;
  white-space:nowrap;transition:all .15s;color:var(--text)}
.btn-pick:hover{border-color:var(--blue);color:var(--blue)}
.btn-run{width:100%;padding:13px;background:var(--blue);color:#fff;
  border:none;border-radius:12px;font-size:.95rem;font-weight:600;
  cursor:pointer;transition:background .15s;margin-top:8px}
.btn-run:hover{background:#0064cc}
.btn-run:disabled{background:#b0b0b8;cursor:not-allowed}
.log-wrap{margin-top:24px;display:none}
.log{background:#1c1c1e;border-radius:12px;padding:16px;
  font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:.75rem;
  color:#e8e8ed;line-height:1.7;max-height:200px;overflow-y:auto}
.log .line-ok{color:#30d158}
.log .line-err{color:#ff453a}
.log .line-info{color:#e8e8ed}
.result{margin-top:20px;padding:16px 20px;border-radius:12px;
  display:none;align-items:center;justify-content:space-between;gap:12px}
.result.success{background:var(--green-lt);border:1px solid #a8e6c0}
.result.error{background:var(--red-lt);border:1px solid #ffc9c7}
.result-text{font-size:.85rem;font-weight:500}
.btn-report{padding:9px 18px;background:var(--green);color:#fff;
  border:none;border-radius:8px;font-size:.82rem;font-weight:600;
  cursor:pointer;text-decoration:none;white-space:nowrap}
.tg-row{display:flex;gap:8px;align-items:center}
.group-select{flex:1;min-width:0;background:var(--bg);border:1.5px solid var(--border);
  border-radius:10px;padding:10px 14px;font-size:.82rem;color:var(--muted);
  appearance:none;cursor:pointer;outline:none;overflow:hidden;text-overflow:ellipsis}
.group-select.loaded{color:var(--text);border-color:var(--blue)}
.group-select:disabled{cursor:default;opacity:.5}
.btn-load{padding:10px 14px;background:var(--white);border:1.5px solid var(--border);
  border-radius:10px;font-size:.82rem;font-weight:500;cursor:pointer;
  white-space:nowrap;transition:all .15s;color:var(--text);flex-shrink:0}
.btn-load:hover{border-color:var(--blue);color:var(--blue)}
.btn-load:disabled{opacity:.5;cursor:not-allowed}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <rect width="28" height="28" rx="8" fill="#0071e3"/>
      <path d="M8 14h12M14 8v12" stroke="white" stroke-width="2.2" stroke-linecap="round"/>
    </svg>
    <span class="logo-text">DupeFinder</span>
  </div>

  <h1>Поиск дубликатов фото</h1>
  <p class="subtitle">Выберите источник и запустите сканирование</p>

  <div class="field">
    <div class="label">Источник данных</div>
    <div class="source-tabs">
      <div class="tab" data-source="telegram" onclick="setSource('telegram')">Telegram</div>
      <div class="tab active" data-source="whatsapp" onclick="setSource('whatsapp')">WhatsApp</div>
    </div>
  </div>

  <div class="field" id="wa-field">
    <div class="label">Папка с экспортом WhatsApp</div>
    <div class="folder-row">
      <div class="folder-path" id="folder-path">Папка не выбрана</div>
      <button class="btn-pick" onclick="pickFolder()">Выбрать...</button>
    </div>
  </div>

  <div class="field" id="tg-field" style="display:none">
    <div class="label">Группа Telegram</div>
    <div class="tg-row">
      <select class="group-select" id="group-select" disabled>
        <option value="">— сначала загрузите список —</option>
      </select>
      <button class="btn-load" id="btn-load" onclick="loadGroups()">Загрузить группы</button>
    </div>
  </div>

  <div class="field">
    <label style="display:flex;align-items:flex-start;gap:10px;cursor:pointer">
      <input type="checkbox" id="use-phash" style="margin-top:3px;accent-color:var(--blue);width:16px;height:16px;flex-shrink:0">
      <span>
        <span style="font-size:.88rem;font-weight:600;color:var(--text)">Искать похожие фото (pHash)</span><br>
        <span style="font-size:.78rem;color:var(--muted)">Находит чуть обрезанные / пережатые копии. Для квитанций с одинаковой суммой может давать ложные срабатывания.</span>
      </span>
    </label>
  </div>

  <div class="field" id="threshold-field" style="display:none">
    <div class="label">Порог похожести: <span id="threshold-val">8</span></div>
    <input type="range" id="threshold" min="1" max="20" value="8"
      oninput="document.getElementById('threshold-val').textContent=this.value"
      style="width:100%;accent-color:var(--blue);margin-top:6px">
    <div style="display:flex;justify-content:space-between;font-size:.72rem;color:var(--muted);margin-top:4px">
      <span>Строже (меньше ложных)</span><span>Мягче (больше находок)</span>
    </div>
  </div>

  <button class="btn-run" id="btn-run" onclick="runScan()">Запустить сканирование</button>
  <button class="btn-clear" id="btn-clear" onclick="clearDb()" style="width:100%;margin-top:8px;padding:10px;background:none;border:1.5px solid var(--border);border-radius:10px;color:var(--muted);cursor:pointer;font-size:.85rem;" onmouseover="this.style.borderColor='#e53935';this.style.color='#e53935'" onmouseout="this.style.borderColor='var(--border)';this.style.color='var(--muted)'">Очистить базу данных</button>

  <div id="progress-wrap" style="display:none;margin-top:12px">
    <div style="display:flex;justify-content:space-between;font-size:.82rem;color:var(--muted);margin-bottom:6px">
      <span id="progress-label">Загрузка...</span>
      <span id="progress-count"></span>
    </div>
    <div style="background:var(--border);border-radius:6px;height:10px;overflow:hidden">
      <div id="progress-fill" style="height:100%;background:var(--blue);width:0%;transition:width .4s ease"></div>
    </div>
  </div>

  <div class="log-wrap" id="log-wrap">
    <div class="log" id="log"></div>
  </div>

  <div class="result" id="result">
    <span class="result-text" id="result-text"></span>
    <a class="btn-report" id="btn-report" href="/report" target="_blank">Открыть отчёт</a>
  </div>
</div>

<script>
let source = 'whatsapp';
let selectedFolder = '';

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('use-phash').addEventListener('change', function() {
    document.getElementById('threshold-field').style.display = this.checked ? 'block' : 'none';
  });
});

function setSource(s) {
  source = s;
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.source === s));
  document.getElementById('wa-field').style.display  = (s !== 'telegram') ? 'block' : 'none';
  document.getElementById('tg-field').style.display  = (s !== 'whatsapp')  ? 'block' : 'none';
  document.getElementById('log-wrap').style.display  = 'none';
  document.getElementById('log').innerHTML           = '';
  document.getElementById('result').style.display    = 'none';
  const btn = document.getElementById('btn-run');
  btn.disabled = false;
  btn.textContent = 'Запустить сканирование';
}

async function loadGroups() {
  const btn = document.getElementById('btn-load');
  const sel = document.getElementById('group-select');
  btn.disabled = true;
  btn.textContent = 'Загружаю...';
  try {
    const res = await fetch('/list-groups');
    if (!res.ok) throw new Error('Ошибка сервера');
    const groups = await res.json();
    sel.innerHTML = '<option value="">— выберите группу —</option>'
      + groups.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
    sel.disabled = false;
    sel.classList.add('loaded');
    btn.textContent = 'Обновить список';
  } catch(e) {
    btn.textContent = 'Ошибка, повторить';
  }
  btn.disabled = false;
}

async function pickFolder() {
  const res = await fetch('/pick-folder');
  const data = await res.json();
  if (data.path) {
    selectedFolder = data.path;
    const el = document.getElementById('folder-path');
    el.textContent = data.path.split('/').pop() || data.path;
    el.title = data.path;
    el.classList.add('selected');
  }
}

function addLog(text, type='info') {
  const log = document.getElementById('log');
  const line = document.createElement('div');
  line.className = 'line-' + type;
  line.textContent = text;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

async function runScan() {
  if (source !== 'telegram' && !selectedFolder) {
    alert('Сначала выберите папку с экспортом WhatsApp');
    return;
  }
  if (source !== 'whatsapp') {
    const sel = document.getElementById('group-select');
    if (!sel.value) { alert('Сначала загрузите список групп и выберите группу'); return; }
  }

  const btn = document.getElementById('btn-run');
  btn.disabled = true;
  btn.textContent = 'Сканирование...';

  const logWrap = document.getElementById('log-wrap');
  const logEl = document.getElementById('log');
  logWrap.style.display = 'block';
  logEl.innerHTML = '';

  document.getElementById('result').style.display = 'none';
  document.getElementById('progress-wrap').style.display = 'none';
  document.getElementById('progress-fill').style.width = '0%';

  const usePhash = document.getElementById('use-phash').checked ? '1' : '0';
  const threshold = document.getElementById('threshold').value;
  const groupId = document.getElementById('group-select')?.value || '';
  const params = new URLSearchParams({ source, folder: selectedFolder, threshold, group: groupId, use_phash: usePhash });
  const es = new EventSource('/run?' + params);

  es.onmessage = (e) => {
    const msg = e.data;
    if (msg.startsWith('DONE:')) {
      es.close();
      document.getElementById('progress-wrap').style.display = 'none';
      showResult(true, 'Готово! Найдено дубликатов: ' + msg.split(':')[2]);
      btn.disabled = false;
      btn.textContent = 'Запустить снова';
    } else if (msg.startsWith('ERROR:')) {
      es.close();
      document.getElementById('progress-wrap').style.display = 'none';
      addLog(msg.replace('ERROR:', ''), 'err');
      showResult(false, 'Ошибка при сканировании');
      btn.disabled = false;
      btn.textContent = 'Запустить снова';
    } else if (msg.startsWith('PROGRESS:')) {
      const parts = msg.split(':');
      const cur = parseInt(parts[1]);
      const total = parseInt(parts[2]);
      const name = parts.slice(3).join(':');
      const pct = total > 0 ? Math.min(Math.round(cur / total * 100), 100) : 0;
      document.getElementById('progress-wrap').style.display = 'block';
      document.getElementById('progress-fill').style.width = pct + '%';
      document.getElementById('progress-label').textContent = name + ': ' + pct + '%';
      document.getElementById('progress-count').textContent = cur.toLocaleString() + ' / ' + total.toLocaleString() + ' фото';
    } else {
      addLog(msg);
    }
  };

  es.onerror = () => {
    es.close();
    showResult(false, 'Соединение прервано');
    btn.disabled = false;
    btn.textContent = 'Запустить снова';
  };
}

function showResult(ok, text) {
  const el = document.getElementById('result');
  el.style.display = 'flex';
  el.className = 'result ' + (ok ? 'success' : 'error');
  document.getElementById('result-text').textContent = text;
  document.getElementById('btn-report').style.display = ok ? '' : 'none';
}

async function clearDb() {
  if (!confirm('Удалить все скачанные фото из базы данных? Потребуется повторное сканирование.')) return;
  const btn = document.getElementById('btn-clear');
  btn.textContent = 'Очищаю...';
  btn.disabled = true;
  const r = await fetch('/clear-db', {method: 'POST'});
  const data = await r.json();
  btn.textContent = 'Очистить базу данных';
  btn.disabled = false;
  if (data.ok) {
    showResult(false, 'База очищена. Запустите сканирование заново.');
  }
}
</script>
</body>
</html>"""


# ── Эндпоинты ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return HTML


@app.route("/clear-db", methods=["POST"])
def clear_db():
    clear_all()
    return jsonify({"ok": True})


@app.route("/list-groups")
def list_groups_endpoint():
    async def _fetch():
        client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
        result = []
        async with client:
            await client.start()
            async for dialog in client.iter_dialogs():
                if isinstance(dialog.entity, (Channel, Chat)):
                    result.append({"id": dialog.id, "name": dialog.name})
        return result
    groups = asyncio.run(_fetch())
    return jsonify(groups)


@app.route("/pick-folder")
def pick_folder():
    import subprocess
    result = subprocess.run(
        ["osascript", "-e",
         'POSIX path of (choose folder with prompt "Выберите папку с экспортом WhatsApp")'],
        capture_output=True, text=True
    )
    path = result.stdout.strip().rstrip("/")
    return jsonify({"path": path if result.returncode == 0 else ""})


@app.route("/run")
def run_scan():
    source    = request.args.get("source", "whatsapp")
    folder    = request.args.get("folder", "")
    threshold  = int(request.args.get("threshold", config.PHASH_THRESHOLD))
    use_phash  = request.args.get("use_phash", "0") == "1"
    group_id_raw = request.args.get("group", "")
    group_ids = [int(group_id_raw)] if group_id_raw else [config.GROUP_1_ID]

    def stream():
        try:
            Path("data").mkdir(exist_ok=True)
            init_db()
            yield "data: Инициализация...\n\n"

            scanned_group_ids = []

            if source in ("whatsapp", "both"):
                if not folder:
                    yield "data: ERROR:Папка WhatsApp не выбрана\n\n"
                    return
                yield f"data: Загружаю WhatsApp из: {Path(folder).name}\n\n"
                wa_gid = load_whatsapp_export(folder)
                if wa_gid:
                    scanned_group_ids.append(wa_gid)

            if source in ("telegram", "both"):
                from downloader import fetch_new_photos
                yield f"data: Подключаюсь к Telegram...\n\n"

                progress_q = queue.Queue()

                def on_progress(current, total, name):
                    progress_q.put(f"PROGRESS:{current}:{total}:{name}")

                def run_tg():
                    async def tg():
                        client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
                        async with client:
                            await client.start()
                            for gid in group_ids:
                                name = await fetch_new_photos(client, gid, on_progress=on_progress)
                                update_group_name(gid, name)
                    asyncio.run(tg())
                    progress_q.put(None)

                t = threading.Thread(target=run_tg)
                t.start()
                while True:
                    msg = progress_q.get()
                    if msg is None:
                        break
                    yield f"data: {msg}\n\n"
                t.join()
                scanned_group_ids.extend(group_ids)

            yield "data: Анализирую дубликаты...\n\n"
            photos = get_photos_by_groups(scanned_group_ids)
            yield f"data: Фото для анализа: {len(photos)}\n\n"

            exact_pairs = find_exact_duplicates(photos)
            exact_hashes = {p["file_hash"] for pair in exact_pairs for p in pair if p.get("file_hash")}
            similar_pairs = find_similar_duplicates(photos, threshold, exact_hashes) if use_phash else []

            yield "data: Генерирую отчёт...\n\n"
            report_path = generate_report(exact_pairs, similar_pairs, total_photos=len(photos))
            total_found = len(exact_pairs) + len(similar_pairs)
            yield f"data: DONE:{report_path}:{total_found}\n\n"

        except Exception as e:
            yield f"data: ERROR:{e}\n\n"

    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/report")
def get_report():
    reports = sorted(Path(config.REPORTS_DIR).glob("report_*.html"), reverse=True)
    if reports:
        return send_file(reports[0])
    return "Отчёт не найден", 404


# ── Запуск ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    def open_browser():
        import time
        time.sleep(1.2)
        webbrowser.open("http://localhost:5001")

    threading.Thread(target=open_browser, daemon=True).start()
    print("Открываю браузер на http://localhost:5001 ...")
    app.run(port=5001, debug=False)
