// При загрузке страницы или по кнопке вызываем:


document.addEventListener('DOMContentLoaded', () => {
    // 1) Привязываем клики ко всем ЖК (добавьте этот класс в openComplexDetails, если ещё нет)
    document.querySelectorAll('.employee-item').forEach(item => {
        item.addEventListener('click', () => {
            const jkName = item.dataset.jk;
            openComplexDetails(jkName);
        });
    });
});

async function openComplexDetails(jkName) {
    const panel = document.getElementById('rightPanel');
    // 2) Показываем панель
    panel.classList.add('active');

    // 3) Подставляем имя ЖК в заголовок / скрытое поле
    document.getElementById('userId').value = jkName;
    document.querySelector('input[name="full_name"]').value = jkName;

    // (опционально) дата добавления
    // document.querySelector('.form-info-data .text-profile.gray').textContent = 'Дата: ' + someDate;

    try {
        // 4) Получаем список файлов
        const resp = await fetch(`/excel/complexes/${encodeURIComponent(jkName)}/files`);
        if (!resp.ok) throw new Error(`${resp.status}`);
        const { files } = await resp.json();

        // 5) Категоризируем
const dataFiles     = files.filter(f => /jk_data\.xlsx$/i.test(f));
const priceFiles    = files.filter(f => /price_shaxamtka\.xlsx$/i.test(f));
const templateFiles = files.filter(f => /contract_template\.docx$/i.test(f)|| /contract_template_empty\.docx$/i.test(f));
const registryFiles = files.filter(f => /contract_registry\.xlsx$/i.test(f)); // NEW

// 6) Получаем контейнеры (теперь 4 секции)
const sections = panel.querySelectorAll('.upload-section .file-list');
const [dataList, pricesList, templateList, registryList] = sections;

// 7) Очищаем
[dataList, pricesList, templateList, registryList].forEach(el => el.innerHTML = '');

// 8) Функция-рендер для одной секции (без изменений, но добавим обработку registry)
function renderFiles(listEl, arr, jkName) {
  if (arr.length === 0) {
    listEl.innerHTML = '<p style="color:#777;">Нет файлов</p>';
    return;
  }
  arr.forEach(fname => {
    const pill = document.createElement('div');
    pill.className = 'file-pill';
    pill.innerHTML = `
      <span>${fname}</span>
            <div class="actions">
              <button type="button" class="edit"   title="Редактировать"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
  <path opacity="0.5" d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" fill="#216BF4"/>
  <path d="M13.9261 14.3019C14.1711 14.1108 14.3933 13.8886 14.8377 13.4442L20.378 7.9038C20.512 7.76986 20.4507 7.53915 20.2717 7.47706C19.6178 7.25017 18.767 6.8242 17.9713 6.02841C17.1755 5.23263 16.7495 4.38192 16.5226 3.72794C16.4605 3.54898 16.2298 3.48767 16.0959 3.62162L10.5555 9.16198C10.1111 9.6064 9.88888 9.8286 9.69778 10.0737C9.47235 10.3627 9.27908 10.6754 9.12139 11.0063C8.98771 11.2868 8.88834 11.5849 8.68959 12.1811L8.43278 12.9516L8.02443 14.1766L7.64153 15.3253C7.54373 15.6187 7.6201 15.9422 7.8388 16.1609C8.0575 16.3796 8.38099 16.456 8.67441 16.3582L9.82308 15.9753L11.0481 15.5669L11.8186 15.3101C12.4148 15.1114 12.7129 15.012 12.9934 14.8783C13.3243 14.7206 13.637 14.5274 13.9261 14.3019Z" fill="#216BF4"/>
  <path d="M22.1123 6.16905C23.2948 4.98656 23.2948 3.06936 22.1123 1.88687C20.9298 0.704377 19.0126 0.704377 17.8302 1.88687L17.652 2.06499C17.4802 2.23687 17.4023 2.47695 17.4452 2.7162C17.4722 2.8667 17.5223 3.08674 17.6134 3.3493C17.7956 3.87439 18.1396 4.56368 18.7876 5.21165C19.4355 5.85961 20.1248 6.20364 20.6499 6.38581C20.9125 6.4769 21.1325 6.52697 21.283 6.55399C21.5223 6.59693 21.7623 6.51905 21.9342 6.34717L22.1123 6.16905Z" fill="#216BF4"/>
</svg></button>
            <button type="button" class="download" title="Скачать"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 32 33" fill="none">
  <path opacity="0.5" fill-rule="evenodd" clip-rule="evenodd" d="M4 19.5C4.55228 19.5 5 19.9477 5 20.5C5 22.4139 5.00212 23.7487 5.13753 24.7559C5.26907 25.7343 5.50967 26.2523 5.87868 26.6213C6.24769 26.9904 6.7658 27.2309 7.74416 27.3625C8.75129 27.4979 10.0861 27.5 12 27.5H20C21.9139 27.5 23.2487 27.4979 24.2559 27.3625C25.2343 27.2309 25.7523 26.9904 26.1213 26.6213C26.4904 26.2523 26.7309 25.7343 26.8625 24.7559C26.9979 23.7487 27 22.4139 27 20.5C27 19.9477 27.4477 19.5 28 19.5C28.5523 19.5 29 19.9477 29 20.5V20.5732C29 22.3967 29 23.8664 28.8447 25.0224C28.6833 26.2225 28.3381 27.2329 27.5356 28.0355C26.7329 28.8381 25.7225 29.1833 24.5224 29.3447C23.3664 29.5 21.8967 29.5 20.0732 29.5H11.9268C10.1034 29.5 8.63363 29.5 7.47767 29.3447C6.27752 29.1833 5.26703 28.8381 4.46447 28.0356C3.66191 27.2329 3.31672 26.2225 3.15536 25.0224C2.99995 23.8664 2.99997 22.3967 3 20.5732C3 20.5488 3 20.5244 3 20.5C3 19.9477 3.44772 19.5 4 19.5Z" fill="#216BF4"/>
  <path fill-rule="evenodd" clip-rule="evenodd" d="M15.9994 3.5C16.2802 3.5 16.5479 3.61803 16.7374 3.82523L22.0707 9.65856C22.4434 10.0662 22.4151 10.6987 22.0075 11.0714C21.5999 11.444 20.9674 11.4157 20.5947 11.0081L16.9994 7.07573V21.8333C16.9994 22.3856 16.5516 22.8333 15.9994 22.8333C15.4471 22.8333 14.9994 22.3856 14.9994 21.8333V7.07573L11.4041 11.0081C11.0314 11.4157 10.3989 11.444 9.99126 11.0714C9.58366 10.6987 9.55532 10.0662 9.92799 9.65856L15.2614 3.82523C15.4508 3.61803 15.7186 3.5 15.9994 3.5Z" fill="#216BF4"/>
</svg></button>
${/contract_registry\.xlsx$/i.test(fname)
          ? `<button type="button" class="sync" title="Синхронизировать">Синхронизировать</button>` // NEW
          : ``}
            </div>
    `;

    // Привязываем действия (добавили ветку для contract_registry.xlsx)
    if (/jk_data\.xlsx$/i.test(fname)) {
      pill.querySelector('.edit').addEventListener('click', () => openChessModal(jkName));
    } else if (/price_shaxamtka\.xlsx$/i.test(fname)) {
      pill.querySelector('.edit').addEventListener('click', () => openPriceModal(jkName));
    } else if (/contract_registry\.xlsx$/i.test(fname)) {
      // если есть спец-модал - используем, иначе fallback на замену файла
      pill.querySelector('.edit').addEventListener('click', () =>
     openReplaceModal(jkName, fname));
    } else {
      // шаблоны договоров и прочее
      pill.querySelector('.edit').addEventListener('click', () => openReplaceModal(jkName, fname));
    }

    // Download
    const downloadBtn = pill.querySelector('.download');
    if (downloadBtn) {
      downloadBtn.addEventListener('click', () => {
        let fileType = '';
        if (/jk_data\.xlsx$/i.test(fname)) {
          fileType = 'jk_data';
        } else if (/price_shaxamtka\.xlsx$/i.test(fname)) {
          fileType = 'price';
        } else if (/contract_template\.docx$/i.test(fname)) {
          fileType = 'template';
        } else if (/contract_registry\.xlsx$/i.test(fname)) {   // NEW
          fileType = 'registry';
        }
        const url = `/excel/complexes/${encodeURIComponent(jkName)}/download?fileType=${fileType}`;
        const link = document.createElement('a');
        link.href = url;
        link.download = fname;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      });
    }
    const syncBtn = pill.querySelector('.sync');
    if (syncBtn) {
      syncBtn.addEventListener('click', async () => {
        const originalText = syncBtn.textContent;
        syncBtn.disabled = true;
        syncBtn.textContent = 'Синхронизируем...';

        try {
          const res = await fetch(`/excel/sync-chess-with-registry?jkName=${encodeURIComponent(jkName)}`, {
            method: 'POST'
          });
          if (!res.ok) {
            const t = await res.text().catch(() => '');
            throw new Error(t || `HTTP ${res.status}`);
          }
          const json = await res.json().catch(() => ({}));
          const updated = typeof json.updated === 'number' ? json.updated : 0;

          syncBtn.textContent = `Готово (${updated}) ✅`;
          // при необходимости обнови модалки/таблицы:
          if (typeof refreshChessGrid === 'function') {
            try { await refreshChessGrid(jkName); } catch (_) {}
          }
          setTimeout(() => {
            syncBtn.textContent = originalText;
            syncBtn.disabled = false;
          }, 1200);
        } catch (e) {
          console.error('Sync error:', e);
          syncBtn.textContent = 'Ошибка ❌';
          setTimeout(() => {
            syncBtn.textContent = originalText;
            syncBtn.disabled = false;
          }, 1800);
        }
      });
    }

    listEl.append(pill);
  });
}

// 9) Рендерим каждую секцию (добавили registry)
renderFiles(dataList,     dataFiles,     jkName);
renderFiles(pricesList,   priceFiles,    jkName);
renderFiles(templateList, templateFiles, jkName);
renderFiles(registryList, registryFiles, jkName); // NEW

    } catch (err) {
        console.error('Ошибка загрузки деталей ЖК:', err);
        panel.querySelectorAll('.upload-section .file-list')
            .forEach(el => el.innerHTML = '<p style="color:red;">Ошибка загрузки</p>');
    }
}

async function loadComplexes() {
    try {
        const response = await fetch('/excel/complexes');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        const complexes = data.complexes || [];

        const listEl = document.querySelector('.employee-list');
        listEl.innerHTML = ''; // очищаем предыдущее содержимое

        complexes.forEach(jkName => {
            const item = document.createElement('div');
            item.className = 'employee-item';
            item.dataset.jk = jkName;
            item.innerHTML = `
          <div class="employee-name">
            ${jkName}
            <i class="fas fa-chevron-right"></i>
          </div>
        `;
            // Клик по комплексу — открываем детали
            item.addEventListener('click', () => openComplexDetails(jkName));
            listEl.append(item);
        });

        if (complexes.length === 0) {
            listEl.innerHTML = '<p>Комплексы не найдены.</p>';
        } else {
            // Автоматически показать детали первого ЖК
            const firstJk = complexes[0];
            openComplexDetails(firstJk);
            // Выделить первый элемент
            const firstItem = listEl.querySelector('.employee-item');
            if (firstItem) firstItem.classList.add('selected');
        }
    } catch (err) {
        console.error('Ошибка при загрузке ЖК:', err);
        document.querySelector('.employee-list').innerHTML =
            '<p style="color:red;">Не удалось загрузить список комплексов.</p>';
    }
}



/**
* Открывает шахматку из jk_data.xlsx в модалке с возможностью менять статус каждой квартиры
*/
async function openChessModal(jkName) {
    // Загрузить JSON шахматки
    const resp = await fetch(`/excel/complexes/${encodeURIComponent(jkName)}/chess`);
    if (!resp.ok) return alert("Не удалось загрузить шахматку");
    const { grid } = await resp.json();
    if (!grid.length) return alert("Данных нет");
  
    // Определяем колонки
    const headers     = Object.keys(grid[0]);
    const aptField    = headers.find(h => /номер\s*помещени/i.test(h));
    const statusField = headers.find(h => /статус/i.test(h));
    const blockField  = headers.find(h => /блок/i.test(h));           // новый
    const floorField  = headers.find(h => /этаж/i.test(h));           // новый
  
  
    // Создаём модалку
    const modal = document.createElement("div");
    modal.className = "custom-modal";
    Object.assign(modal.style, {
      position: "fixed", inset: 0,
      background: "rgba(0,0,0,0.5)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 2000
    });
    const content = document.createElement("div");
    Object.assign(content.style, {
      width: "90%", maxWidth: "800px", maxHeight: "80vh", overflow: "auto",
      background: "#fff", padding: "20px", borderRadius: "8px"
    });
  
    // Собираем HTML таблицы
    let html = `<h3>Шахматка ЖК “${jkName}”</h3>`;
    html += `<table style="width:100%; border-collapse:collapse; text-align:center;">`;
    // Заголовки
    html += "<thead><tr>";
    headers.forEach(h => {
      html += `<th style="border:1px solid #ccc; padding:6px;">${h}</th>`;
    });
    html += "</tr></thead><tbody>";
    // Данные
    grid.forEach((rowObj, rowIdx) => {
      // Определяем цвет фона по текущему статусу
      const statusValue = String(rowObj[statusField]).toLowerCase().trim();
      let bgColor = '';
      if (statusValue === 'свободна') {
          bgColor = '#e0f8e0'; // светло-зелёный
      } else if (statusValue === 'продана') {
          bgColor = '#f8e0e0'; // светло-красный
      } else if (statusValue === 'бронь') {
          bgColor = '#f8f4e0'; // светло-жёлтый
      }
      html += `<tr style="background-color: ${bgColor}">`;
      headers.forEach(col => {
        const val = rowObj[col] ?? "";

        
        if (col === statusField) {
            statusLower = val.toLowerCase().trim();
          html += `<td style="border:1px solid #ccc; padding:4px;">
            <select data-row="${rowIdx}">
              <option${statusLower==="свободна"?" selected":""}>свободна</option>
              <option${statusLower==="продана"  ?" selected":""}>продана</option>
              <option${statusLower==="бронь"    ?" selected":""}>бронь</option>
            </select>
          </td>`;
        } else {
          html += `<td style="border:1px solid #ccc; padding:6px;">${val}</td>`;
        }
      });
      html += "</tr>";
    });
    html += "</tbody></table>";
    // Кнопки
    html += `
      <div style="text-align:right; margin-top:12px;">
        <button id="saveChessBtn">Сохранить</button>
        <button id="closeChessBtn" style="margin-left:8px;">Закрыть</button>
      </div>
    `;
  
    content.innerHTML = html;
    modal.appendChild(content);
    document.body.appendChild(modal);
  
    // Закрыть
    document.getElementById("closeChessBtn").onclick = () => modal.remove();
  
    
    // Подготовим кнопку: оборачиваем текст и добавляем спиннер один раз
(function prepareSaveBtn(){
  const btn = document.getElementById("saveChessBtn");
  if (!btn) return;
  if (!btn.querySelector('.btn-label')) {
    const label = document.createElement('span');
    label.className = 'btn-label';
    label.textContent = btn.textContent.trim() || 'Сохранить';

    const spinner = document.createElement('span');
    spinner.className = 'btn-spinner';
    // SVG-спиннер (монохромный, берёт цвет от currentColor)
    spinner.innerHTML = `
      <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
        <circle cx="12" cy="12" r="9.5" fill="none" stroke="currentColor" stroke-width="4" opacity="0.2"/>
        <path d="M12 2.5a9.5 9.5 0 0 1 9.5 9.5" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
      </svg>
    `;

    btn.textContent = '';
    btn.appendChild(spinner);
    btn.appendChild(label);
  }
})();

function setBtnLoading(btn, isLoading) {
  const label = btn.querySelector('.btn-label');
  if (isLoading) {
    btn.classList.remove('is-success','is-error');
    btn.classList.add('is-loading');
    btn.disabled = true;
    btn.setAttribute('aria-busy', 'true');
    label.textContent = 'Сохраняем...';
  } else {
    btn.classList.remove('is-loading');
    btn.removeAttribute('aria-busy');
    btn.disabled = false;
  }
}

function setBtnResult(btn, type, text) {
  const label = btn.querySelector('.btn-label');
  btn.classList.remove('is-loading','is-success','is-error');
  btn.classList.add(type === 'success' ? 'is-success' : 'is-error');
  label.textContent = text;
}

// Твой обработчик с лоадером/результатами
document.getElementById("saveChessBtn").onclick = async () => {
  const btn = document.getElementById("saveChessBtn");

  // Собираем обновления
  const selects = content.querySelectorAll("select[data-row]");
  const updates = Array.from(selects).map(sel => {
    const rowIdx = +sel.dataset.row;
    const rowObj = grid[rowIdx];
    return {
      jkName:          jkName,
      blockName:       rowObj[blockField],
      floor:           Number(rowObj[floorField]),
      apartmentNumber: rowObj[aptField],
      newStatus:       sel.value
    };
  });

  setBtnLoading(btn, true);

  try {
    const saveResp = await fetch('/excel/complexes/chess', {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ updates })
    });

    if (!saveResp.ok) {
      const errBody = await saveResp.text();
      console.error("Server responded:", errBody);
      throw new Error(saveResp.status);
    }

    setBtnResult(btn, 'success', 'Сохранено ✅');

    // закрываем модалку спустя короткую паузу
    setTimeout(() => {
      modal.remove?.();
    }, 900);

  } catch (e) {
    console.error(e);
    setBtnResult(btn, 'error', 'Ошибка ❌');
    // вернуть кнопку в исходное состояние через 2 сек
    setTimeout(() => {
      const label = btn.querySelector('.btn-label');
      btn.classList.remove('is-success','is-error');
      label.textContent = 'Сохранить';
      setBtnLoading(btn, false);
    }, 2000);
  }
};
      }
  
/**
 * Открывает модальное окно для замены файла
 * @param {string} jkName - имя ЖК
 * @param {string} oldFilename - имя текущего файла
 */
function openReplaceModal(jkName, oldFilename) {
  // Создаем overlay
  const modal = document.createElement('div');
  modal.className = 'custom-modal';
  Object.assign(modal.style, {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000
  });
  // Контент
  const content = document.createElement('div');
  Object.assign(content.style, {
    background: '#fff', padding: '20px', borderRadius: '8px', width: '90%', maxWidth: '400px'
  });
  content.innerHTML = `
    <div class="upload-section">
      <div class="upload-header">
        <span>Заменить файл ${oldFilename}</span>
      </div>
      <label class="dropzone" for="replaceInput">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M12 16.5v-9m0 0L8.25 10.5m3.75-3V10.5m0-3L15.75 10.5M3 20.25h18a2.25 2.25 0 002.25-2.25V5.25A2.25 2.25 0 0021 3H3a2.25 2.25 0 00-2.25 2.25v12.75A2.25 2.25 0 003 20.25z"/>
        </svg>
        Перетащите файл или нажмите
      </label>
      <input type="file" id="replaceInput" accept=".xlsx,.xls,.csv,.docx,.doc" multiple style="display:none;" />
      <div class="file-list" id="replace-list"></div>
    </div>
    <div style="text-align:right; margin-top:12px;">
      <button id="saveReplaceBtn" disabled>Сохранить</button>
      <button id="cancelReplaceBtn" style="margin-left:8px;">Отмена</button>
    </div>
  `;
 
  modal.appendChild(content);
  document.body.appendChild(modal);

  const input = content.querySelector('#replaceInput');
  const saveBtn = content.querySelector('#saveReplaceBtn');
  const cancelBtn = content.querySelector('#cancelReplaceBtn');

  // Реализация выбора файла: скрываем dropzone, показываем pill
  const dropzoneLabel = content.querySelector('label.dropzone');
  const fileList = content.querySelector('#replace-list');
  input.addEventListener('change', () => {
    if (!input.files.length) return;
    const file = input.files[0];
    // hide dropzone and input
    dropzoneLabel.style.display = 'none';
    input.style.display = 'none';
    // enable save button
    saveBtn.disabled = false;
    // show pill
    fileList.innerHTML = `
      <div class="file-pill">
        <span>${file.name}</span>
        <button type="button" class="delete">🗑️</button>
      </div>`;
    // handle delete pill
    fileList.querySelector('.delete').addEventListener('click', () => {
      fileList.innerHTML = '';
      input.value = '';
      saveBtn.disabled = true;
      dropzoneLabel.style.display = 'flex';
      // input remains hidden
    });
  });

  // Отмена
  cancelBtn.addEventListener('click', () => modal.remove());

  // Сохранение: отправляем замену на сервер
  saveBtn.addEventListener('click', async () => {
    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', oldFilename.match(/jk_data\.xlsx$/i) ? 'jk_data' :
                                 oldFilename.match(/price_shaxamtka\.xlsx$/i) ? 'price' :
                                 oldFilename.match(/contract_registry\.xlsx$/i) ? 'registry':
                                 oldFilename.match(/contract_template_empty\.docx$/i) ? 'template_empty':
                                 'template');
    formData.append('name', jkName);
    try {
      const resp = await fetch(`/excel/replace-file`, {
        method: 'POST',
        body: formData
      });
      const result = await resp.json();
      if (!resp.ok) throw new Error(result.detail || result.message);
      // После успешного сохранения обновляем список файлов:
      openComplexDetails(jkName);
      modal.remove();
      showNotification('Файл заменён', 'success');
    } catch (err) {
      console.error(err);
      showNotification('Ошибка замены файла', 'error');
    }
  });
}

// Вызываем при старте:
document.addEventListener('DOMContentLoaded', loadComplexes);
/**
 * Открывает модальное окно для редактирования прайса ЖК
 * @param {string} jkName - имя ЖК
 */
async function openPriceModal(jkName) {
    // Загрузить данные прайса в формате JSON
    const resp = await fetch(`/excel/complexes/${encodeURIComponent(jkName)}/price`);
    if (!resp.ok) return alert("Не удалось загрузить прайс");
    const { headers, rows } = await resp.json();
  
    // Создать модалку
    const modal = document.createElement("div");
    modal.className = "custom-modal";
    Object.assign(modal.style, {
      position: "fixed", inset: 0,
      background: "rgba(0,0,0,0.5)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 2000
    });
    const content = document.createElement("div");
    Object.assign(content.style, {
      width: "90%", maxWidth: "800px", maxHeight: "80vh", overflow: "auto",
      background: "#fff", padding: "20px", borderRadius: "8px"
    });
  
    // Создаем таблицу с учетом структуры данных из скриншота
    // Первая колонка - "Этаж" (неизменяемая)
    // Все остальные колонки - цены (изменяемые)
    let html = `<h3>Редактирование прайса ЖК "${jkName}"</h3>`;
    html += `<table style="width:100%; border-collapse:collapse; text-align:left;">`;
    
    // Шапка таблицы
    html += "<thead><tr>";
    headers.forEach((col, colIdx) => {
        if (colIdx > 0 && typeof col === 'number') {
          // format percent header
          const pct = Math.round(col * 100) + '%';
          html += `<th>${pct}</th>`;
        } else {
          html += `<th>${col}</th>`;
        }
      });
    html += "</tr></thead><tbody>";
    
    // Строки с данными
    rows.forEach((row, rowIdx) => {
      html += "<tr>";
      
      // Обрабатываем каждую ячейку в строке
      headers.forEach((col, colIdx) => {
        const value = row[col] != null ? row[col] : "";
        
        // Проверяем, является ли это колонкой "Этаж" (обычно первая колонка)
        const isFloorColumn = colIdx === 0 || (typeof col === 'string' && col.toLowerCase().includes('этаж'));
        
        if (isFloorColumn) {
          // Колонка "Этаж" - только для чтения
          html += `<td>${value}</td>`;
        } else {
          // Все остальные колонки (цены) - редактируемые
          html += `<td>
            <input 
              type="text" 
              data-row="${rowIdx}" 
              data-col="${col}" 
              data-col-index="${colIdx}" 
              value="${value}" 
              style="width: 100%; box-sizing: border-box;"
            />
          </td>`;
        }
      });
      html += "</tr>";
    });
    
    html += "</tbody></table>";
    
    // Кнопки управления
    html += `
      <div style="text-align:right; margin-top:12px;">
        <button id="savePriceBtn">Сохранить</button>
        <button id="cancelPriceBtn" style="margin-left:8px;">Отмена</button>
      </div>
    `;
    
    content.innerHTML = html;
    modal.appendChild(content);
    document.body.appendChild(modal);
  
    // Обработчики ввода - только цифры
    content.querySelectorAll('input[data-row][data-col]').forEach(input => {
      input.addEventListener('input', (e) => {
        // Удаляем все символы кроме цифр
        e.target.value = e.target.value.replace(/[^\d]/g, '');
      });
    });
  
    // Обработчики кнопок
    content.querySelector("#cancelPriceBtn").onclick = () => modal.remove();
    content.querySelector("#savePriceBtn").onclick = async () => {
      // Собрать обновлённые данные
      const updatedRows = JSON.parse(JSON.stringify(rows));
      const inputs = content.querySelectorAll('input[data-row][data-col]');
      
      inputs.forEach(input => {
        const rowIdx = +input.dataset.row;
        const colName = input.dataset.col;
        // Преобразуем в число
        const numericValue = parseInt(input.value, 10);
        
        // Обновляем только если это валидное число
        if (!isNaN(numericValue)) {
          updatedRows[rowIdx][colName] = numericValue;
        }
      });
      
      try {
        const saveResp = await fetch(
          `/excel/complexes/${encodeURIComponent(jkName)}/price`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ headers, rows: updatedRows })
          }
        );
        
        if (!saveResp.ok) {
          const errorData = await saveResp.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Ошибка сервера');
        }
        
        alert("Прайс сохранён успешно");
        modal.remove();
      } catch (e) {
        alert(`Ошибка при сохранении прайса: ${e.message}`);
      }
    };
  }