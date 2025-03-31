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
    modalContent.style.backgroundColor = '#fff';
    modalContent.style.padding = '20px';
    modalContent.style.borderRadius = '8px';
    modalContent.style.maxHeight = '90vh';
    modalContent.style.overflowY = 'auto';
    modalContent.style.width = '90%';
    modalContent.style.maxWidth = '1000px';

    // Список жилых комплексов (можно динамически получать с сервера)
    const jkList = ["ЖК_Бахор", "ЖК_Другой"]; // Замените на реальный список или запрос к API

    modalContent.innerHTML = `
        <h3 style="margin-top: 0;">Реестр договоров</h3>
        <div style="margin-bottom: 15px;">
            <label for="jk-select">Выберите жилой комплекс:</label>
            <select id="jk-select" style="padding: 5px; width: 200px;">
                ${jkList.map(jk => `<option value="${jk}">${jk}</option>`).join('')}
            </select>
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

    // Функция загрузки данных реестра
    function loadRegistry(jkName) {
        fetch(`/api/get-contract-registry?jkName=${encodeURIComponent(jkName)}`)
            .then(response => {
                if (!response.ok) {
                    if (response.status === 404) {
                        throw new Error("Реестр договоров не найден");
                    }
                    throw new Error("Ошибка при загрузке реестра");
                }
                return response.json();
            })
            .then(data => {
                if (data.registry.length === 0) {
                    tableContainer.innerHTML = "<p>Реестр пуст</p>";
                    downloadButton.disabled = true;
                    return;
                }

                const table = document.createElement("table");
                table.style.width = "100%";
                table.style.borderCollapse = "collapse";
                table.style.fontSize = "14px";

                const thead = document.createElement("thead");
                const headerRow = document.createElement("tr");
                Object.keys(data.registry[0]).forEach(header => {
                    const th = document.createElement("th");
                    th.textContent = header;
                    th.style.border = "1px solid #ddd";
                    th.style.padding = "8px";
                    th.style.backgroundColor = "#f2f2f2";
                    headerRow.appendChild(th);
                });
                thead.appendChild(headerRow);
                table.appendChild(thead);

                const tbody = document.createElement("tbody");
                data.registry.forEach(row => {
                    const tr = document.createElement("tr");
                    Object.values(row).forEach(value => {
                        const td = document.createElement("td");
                        td.textContent = value;
                        td.style.border = "1px solid #ddd";
                        td.style.padding = "8px";
                        tr.appendChild(td);
                    });
                    tbody.appendChild(tr);
                });
                table.appendChild(tbody);

                tableContainer.innerHTML = "";
                tableContainer.appendChild(table);
                downloadButton.disabled = false;

                // Обработчик кнопки скачивания
                downloadButton.onclick = () => {
                    const url = `/api/download-contract-registry?jkName=${encodeURIComponent(jkName)}`;
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = `contract_registry_${jkName}.xlsx`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                };
            })
            .catch(error => {
                console.error("Ошибка:", error);
                tableContainer.innerHTML = `<p style="color: red;">${error.message}</p>`;
                downloadButton.disabled = true;
            });
    }

    const initialJk = jkSelect.value; // Первый элемент из списка
    loadRegistry(initialJk);
    // Загрузка данных при выборе ЖК
    jkSelect.addEventListener("change", (e) => {
        const selectedJk = e.target.value;
        loadRegistry(selectedJk);
    });

    // Закрытие модального окна
    modalContent.querySelector(".close-modal").addEventListener("click", () => {
        modal.remove();
    });
}