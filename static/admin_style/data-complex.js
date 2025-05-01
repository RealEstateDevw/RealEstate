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
        const dataFiles = files.filter(f => /jk_data\.xlsx$/i.test(f));
        const priceFiles = files.filter(f => /price_shaxamtka\.xlsx$/i.test(f));
        const templateFiles = files.filter(f => /contract_template\.docx$/i.test(f));

        // 6) Получаем контейнеры
        const sections = panel.querySelectorAll('.upload-section .file-list');
        const [dataList, pricesList, templateList] = sections;

        // 7) Очищаем
        [dataList, pricesList, templateList].forEach(el => el.innerHTML = '');

        // 8) Функция-рендер для одной секции
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
              <button type="button" class="edit"   title="Редактировать">✏️</button>
            </div>
          `;
                // Привязываем действия
                // Привязываем действия
                if (/jk_data\.xlsx$/i.test(fname)) {
                    // Для шахматки вызываем свой модал
                    pill.querySelector('.edit').addEventListener('click', () => openChessModal(jkName));
                } else if (/price_shaxamtka\.xlsx$/i.test(fname)) {
                    pill.querySelector('.edit').addEventListener('click', () => openPriceModal(jkName));
                } else {
                    pill.querySelector('.edit').addEventListener('click', () => openReplaceModal(jkName, fname));
                }
               
                listEl.append(pill);
            });
        }

        // 9) Рендерим каждую секцию
        renderFiles(dataList, dataFiles, jkName);
        renderFiles(pricesList, priceFiles, jkName);
        renderFiles(templateList, templateFiles, jkName);

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
        console.log(rowIdx);
        
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
  
    
        document.getElementById("saveChessBtn").onclick = async () => {
            const selects = content.querySelectorAll("select[data-row]");
            const updates = Array.from(selects).map(sel => {
              const rowIdx = +sel.dataset.row;
              const rowObj = grid[rowIdx];
              return {
                jkName:          jkName,                       // теперь передаём ЖК внутри объекта
                blockName:       rowObj[blockField],           // Блок
                floor:           Number(rowObj[floorField]),    // Этаж
                apartmentNumber: rowObj[aptField],              // Номер квартиры (может быть строкой)
                newStatus:       sel.value                      // Новый статус
              };
            });
        

        
            try {
              const saveResp = await fetch(
                '/excel/complexes/chess',
                {
                  method: "PUT",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ updates })
                }
              );
              if (!saveResp.ok) {
                const errBody = await saveResp.text();
                console.error("Server responded:", errBody);
                throw new Error(saveResp.status);
              }
              alert("Статусы сохранены");
              modal.remove();
            } catch (e) {
              alert("Ошибка при сохранении: " + e);
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