document.addEventListener("DOMContentLoaded", () => {
    // Находим кнопку "Реестр Договоров"
    const registryButton = document.querySelector(".header .shahmatki:first-child");
    if (registryButton) {
        registryButton.addEventListener("click", (e) => {
            e.preventDefault(); // Предотвращаем переход, если это ссылка
            openRegistryModal();
        });
    }
});

// Функция открытия модального окна для реестра
function openRegistryModal() {
    const existingModal = document.querySelector(".custom-modal");
    if (existingModal) existingModal.remove();

    const modal = document.createElement("div");
    modal.className = "custom-modal";
    // ... (стили модального окна остаются прежними) ...
    modal.style.position = 'fixed';
    modal.style.left = '0';
    modal.style.top = '0';
    modal.style.width = '100%';
    modal.style.height = '100%';
    modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
    modal.style.display = 'flex';
    modal.style.justifyContent = 'center';
    modal.style.alignItems = 'center';
    modal.style.zIndex = '1000';


    const modalContent = document.createElement('div');
    modalContent.className = 'custom-modal-content';
    // ... (стили контента остаются прежними) ...
    modalContent.style.backgroundColor = '#fff';
    modalContent.style.padding = '20px';
    modalContent.style.borderRadius = '8px';
    modalContent.style.maxHeight = '90vh';
    modalContent.style.overflowY = 'auto';
    modalContent.style.width = '90%';
    modalContent.style.maxWidth = '1100px'; // Немного увеличим ширину для кнопки

    const jkList = ["ЖК_Бахор", "ЖК_Рассвет"]; // Замените или получите список с API

    modalContent.innerHTML = `
        <h3 style="margin-top: 0;">Реестр договоров</h3>
        <div style="margin-bottom: 15px;">
            <label for="jk-select">Выберите жилой комплекс:</label>
            <select id="jk-select" style="padding: 5px; width: 200px;">
                ${jkList.map(jk => `<option value="${jk}">${jk}</option>`).join('')}
            </select>
            <span id="loading-indicator" style="margin-left: 10px; display: none;">Загрузка...</span>
            <span id="error-message" style="margin-left: 10px; color: red; display: none;"></span>
        </div>
        <div id="registry-table-container">
            <p>Выберите жилой комплекс для загрузки данных...</p>
        </div>
        <div style="margin-top: 15px; display: flex; justify-content: space-between;">
            <button id="download-registry-btn" class="action-btn" disabled>Скачать реестр</button>
            <button type="button" class="close-modal action-btn secondary">Закрыть</button>
        </div>
    `;

    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    const jkSelect = modalContent.querySelector("#jk-select");
    const tableContainer = modalContent.querySelector("#registry-table-container");
    const downloadButton = modalContent.querySelector("#download-registry-btn");
    const loadingIndicator = modalContent.querySelector("#loading-indicator");
    const errorMessageSpan = modalContent.querySelector("#error-message");

    // --- Функция удаления договора ---
    function handleDeleteContract(jkName, contractNumber, buttonElement) {
        // Запрос подтверждения у пользователя
        if (!confirm(`Вы уверены, что хотите удалить договор ${contractNumber} из реестра ${jkName}? Это действие необратимо.`)) {
            return; // Пользователь отменил
        }

        // Блокируем кнопку на время запроса
        buttonElement.disabled = true;
        buttonElement.textContent = 'Удаление...';
        errorMessageSpan.style.display = 'none'; // Скрыть старые ошибки

        const deleteUrl = `/excel/delete-contract-from-registry?jkName=${encodeURIComponent(jkName)}&contractNumber=${encodeURIComponent(contractNumber)}`;

        fetch(deleteUrl, {
            method: 'DELETE',
        })
        .then(response => {
            if (!response.ok) {
                 // Попытка прочитать тело ошибки, если оно есть
                return response.json().then(err => { throw new Error(err.detail || `Ошибка ${response.status}: Не удалось удалить договор`); });
            }
            return response.json(); // Ожидаем JSON с сообщением об успехе
        })
        .then(data => {
            console.log('Удаление успешно:', data);
            alert(data.message || 'Договор успешно удален.'); // Показать сообщение от сервера
            // Перезагружаем данные реестра для этого ЖК, чтобы обновить таблицу
            loadRegistry(jkName);
        })
        .catch(error => {
            console.error("Ошибка при удалении:", error);
            errorMessageSpan.textContent = `Ошибка удаления: ${error.message}`;
            errorMessageSpan.style.display = 'inline';
             // Разблокируем кнопку в случае ошибки
             buttonElement.disabled = false;
             buttonElement.textContent = 'Удалить';
        });
    }


    // --- Функция загрузки данных реестра (обновленная) ---
    function loadRegistry(jkName) {
        tableContainer.innerHTML = ""; // Очистить предыдущую таблицу
        loadingIndicator.style.display = 'inline'; // Показать индикатор загрузки
        errorMessageSpan.style.display = 'none'; // Скрыть старые ошибки
        downloadButton.disabled = true; // Блокируем кнопку скачивания на время загрузки

        fetch(`/excel/get-contract-registry?jkName=${encodeURIComponent(jkName)}`)
            .then(response => {
                if (!response.ok) {
                    // Попытка прочитать тело ошибки, если оно есть
                    return response.json().then(err => { throw new Error(err.detail || `Ошибка ${response.status}: Не удалось загрузить реестр`); });
                }
                return response.json();
            })
            .then(data => {
                loadingIndicator.style.display = 'none'; // Скрыть индикатор

                if (!data.registry || data.registry.length === 0) {
                    tableContainer.innerHTML = "<p>Реестр пуст или не найден.</p>";
                    downloadButton.disabled = true;
                    return;
                }

                const table = document.createElement("table");
                table.style.width = "100%";
                table.style.borderCollapse = "collapse";
                table.style.fontSize = "13px"; // Можно немного уменьшить шрифт

                const thead = document.createElement("thead");
                const headerRow = document.createElement("tr");

                // Получаем заголовки из первой строки данных
                const headers = Object.keys(data.registry[0]);

                headers.forEach(header => {
                    const th = document.createElement("th");
                    th.textContent = header;
                    th.style.border = "1px solid #ddd";
                    th.style.padding = "6px"; // Уменьшим padding
                    th.style.backgroundColor = "#f2f2f2";
                    th.style.textAlign = "left";
                    headerRow.appendChild(th);
                });

                 // --- Добавляем заголовок для колонки "Действия" ---
                const thAction = document.createElement("th");
                thAction.textContent = "Действия";
                thAction.style.border = "1px solid #ddd";
                thAction.style.padding = "6px";
                thAction.style.backgroundColor = "#f2f2f2";
                headerRow.appendChild(thAction);
                thead.appendChild(headerRow);
                table.appendChild(thead);


                const tbody = document.createElement("tbody");
                data.registry.forEach(row => {
                    const tr = document.createElement("tr");
                    // --- ВАЖНО: Получаем номер договора из данных строки ---
                    // Убедитесь, что ключ '№ Договора' точно соответствует заголовку в вашем Excel
                    const contractNumber = row['№ Договора'];
                    if (!contractNumber) {
                        console.warn("Строка без номера договора:", row); // Предупреждение, если нет номера
                    }

                    // Заполняем ячейки данными
                    headers.forEach(header => {
                        const td = document.createElement("td");
                        // Проверяем на null/undefined перед отображением
                        td.textContent = row[header] !== null && row[header] !== undefined ? row[header] : '';
                        td.style.border = "1px solid #ddd";
                        td.style.padding = "6px";
                        tr.appendChild(td);
                    });


                    // --- Добавляем ячейку с кнопкой "Удалить" ---
                    const tdAction = document.createElement("td");
                    tdAction.style.border = "1px solid #ddd";
                    tdAction.style.padding = "6px";
                    tdAction.style.textAlign = "center";

                    if(contractNumber){ // Добавляем кнопку только если есть номер договора
                        const deleteButton = document.createElement("button");
                        deleteButton.textContent = "Удалить";
                        deleteButton.className = "action-btn danger-btn"; // Добавим класс для стилизации
                        deleteButton.style.padding = '3px 8px';
                        deleteButton.style.fontSize = '12px';
                        deleteButton.style.cursor = 'pointer';
                        // Добавляем обработчик клика
                        deleteButton.onclick = () => handleDeleteContract(jkName, contractNumber, deleteButton);
                        tdAction.appendChild(deleteButton);
                    } else {
                         tdAction.textContent = '-'; // Если номера нет, ставим прочерк
                    }

                    tr.appendChild(tdAction);
                    tbody.appendChild(tr);
                });
                table.appendChild(tbody);

                tableContainer.innerHTML = ""; // Очистить сообщение "Реестр пуст"
                tableContainer.appendChild(table);
                downloadButton.disabled = false; // Разблокируем кнопку скачивания

                // Обновляем обработчик кнопки скачивания (на всякий случай, если jkName изменился)
                downloadButton.onclick = () => {
                    // --- ПРЕДПОЛАГАЕМ, что есть отдельный эндпоинт для скачивания ---
                    // Если его нет, нужно будет генерировать файл на лету или скачивать существующий
                    const downloadUrl = `/excel/download-contract-registry?jkName=${encodeURIComponent(jkName)}`; // УКАЖИТЕ ПРАВИЛЬНЫЙ URL!
                    const link = document.createElement("a");
                    link.href = downloadUrl; // URL эндпоинта, который отдает файл
                    link.download = `contract_registry_${jkName}.xlsx`; // Имя файла при скачивании
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                };

            })
            .catch(error => {
                console.error("Ошибка загрузки реестра:", error);
                loadingIndicator.style.display = 'none'; // Скрыть индикатор
                tableContainer.innerHTML = ""; // Очистить таблицу
                errorMessageSpan.textContent = `Ошибка загрузки: ${error.message}`;
                errorMessageSpan.style.display = 'inline'; // Показать сообщение об ошибке
                downloadButton.disabled = true;
            });
    }

    // --- Инициализация и обработчики событий ---
    const initialJk = jkSelect.value;
    if (initialJk) { // Загружаем, только если есть выбранное значение
        loadRegistry(initialJk);
    }

    jkSelect.addEventListener("change", (e) => {
        const selectedJk = e.target.value;
        loadRegistry(selectedJk);
    });

    modalContent.querySelector(".close-modal").addEventListener("click", () => {
        modal.remove();
    });

    // Добавим стили для кнопки удаления (опционально)
    const styleSheet = document.createElement("style");
    styleSheet.type = "text/css";
    styleSheet.innerText = `
        .action-btn { padding: 8px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .action-btn.secondary { background-color: #ccc; color: #333; }
        .action-btn.danger-btn { background-color: #f44336; color: white; }
        .action-btn:disabled { background-color: #e0e0e0; cursor: not-allowed; }
        .custom-modal-content { max-width: 1100px; } /* Увеличили ширину */
    `;
    document.head.appendChild(styleSheet);
}