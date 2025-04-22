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
        function renderFiles(listEl, arr) {
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
              <button type="button" class="delete" title="Удалить">🗑️</button>
            </div>
          `;
                // Привязываем действия
                // Привязываем действия
                if (/jk_data\.xlsx$/i.test(fname)) {
                    // Для шахматки вызываем свой модал
                    pill.querySelector('.edit').addEventListener('click', () => openChessModal(jkName));
                } else {
                    pill.querySelector('.edit').addEventListener('click', () => {
                        // TODO: open editor для других файлов
                        alert(`Редактировать ${fname}`);
                    });
                }
                pill.querySelector('.delete').addEventListener('click', () => {
                    // TODO: удалить файл через API
                    if (confirm(`Удалить файл ${fname}?`)) {
                        deleteComplexFile(jkName, fname, listEl, pill);
                    }
                });
                listEl.append(pill);
            });
        }

        // 9) Рендерим каждую секцию
        renderFiles(dataList, dataFiles);
        renderFiles(pricesList, priceFiles);
        renderFiles(templateList, templateFiles);

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
              <option${statusLower==="свободна"?" selected":""}>Свободно</option>
              <option${statusLower==="продана"  ?" selected":""}>Продана</option>
              <option${statusLower==="бронь"    ?" selected":""}>Бронь</option>
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
  
    // Сохранить
    document.getElementById("saveChessBtn").onclick = async () => {
        const selects = content.querySelectorAll("select[data-row]");
        const updates = Array.from(selects).map(sel => {
          const rowIdx = +sel.dataset.row;
          return {
            apt:     String(grid[rowIdx][aptField]),  // номер помещения из grid
            status: sel.value
          };
        });
      
        // ---- Дебаг ----
        console.log("aptField:", aptField);
        console.log("updates array:", updates);
        console.log("payload JSON:", JSON.stringify({ updates }));
      
        try {
          const saveResp = await fetch(
            `/excel/complexes/${encodeURIComponent(jkName)}/chess`, {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ updates })
            }
          );
          if (!saveResp.ok) {
            const errBody = await saveResp.text();
            console.error("Server responded 422 with body:", errBody);
            throw new Error(saveResp.status);
          }
          alert("Статусы сохранены");
          modal.remove();
        } catch (e) {
          alert("Ошибка при сохранении: " + e);
        }
      };
  }
// Вызываем при старте:
document.addEventListener('DOMContentLoaded', loadComplexes);