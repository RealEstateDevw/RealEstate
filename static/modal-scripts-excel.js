document.addEventListener("DOMContentLoaded", () => {
    const registryButton = document.querySelector(".header .shahmatki:first-child");
    if (registryButton) {
        registryButton.addEventListener("click", (e) => {
            e.preventDefault();
            openRegistryModal();
        });
    }
});

function openRegistryModal() {
    const existingModal = document.querySelector(".registry-modal");
    if (existingModal) existingModal.remove();

    const modal = document.createElement("div");
    modal.className = "custom-modal registry-modal";
    modal.innerHTML = `
        <div class="custom-modal__overlay"></div>
        <div class="custom-modal__panel" role="dialog" aria-modal="true">
            <div class="custom-modal__header">
                <div>
                    <h3 class="custom-modal__title">Реестр договоров</h3>
                    <p class="custom-modal__subtitle">Выберите жилой комплекс, чтобы увидеть актуальный реестр</p>
                </div>
                <button type="button" class="close-modal custom-modal__close" aria-label="Закрыть">
                    <span></span><span></span>
                </button>
            </div>
            <div class="custom-modal__controls">
                <label for="jk-select" class="control-label">Жилой комплекс</label>
                <div class="control-select">
                    <select id="jk-select"></select>
                    <span id="loading-indicator" class="control-loading">Загрузка…</span>
                    <span id="error-message" class="control-error"></span>
                </div>
            </div>
            <div id="registry-table-container" class="registry-table__wrapper">
                <p class="registry-table__placeholder">Выберите жилой комплекс для загрузки данных…</p>
            </div>
            <div class="custom-modal__footer">
                <button id="download-registry-btn" class="action-btn primary" disabled>
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16a1 1 0 0 1-.7-.3l-4-4a1 1 0 0 1 1.4-1.4L11 12.17V4a1 1 0 0 1 2 0v8.17l2.3-1.9a1 1 0 0 1 1.4 1.46l-4 3.5A1 1 0 0 1 12 16Zm8 4H4a1 1 0 0 1 0-2h16a1 1 0 0 1 0 2Z"></path></svg>
                    Скачать реестр
                </button>
                <button type="button" class="close-modal action-btn secondary">Закрыть</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    const jkList = ["ЖК_Бахор", "ЖК_Рассвет"];
    const jkSelect = modal.querySelector("#jk-select");
    jkSelect.innerHTML = jkList.map(jk => `<option value="${jk}">${jk}</option>`).join("");

    const modalPanel = modal.querySelector(".custom-modal__panel");
    const tableContainer = modal.querySelector("#registry-table-container");
    const downloadButton = modal.querySelector("#download-registry-btn");
    const loadingIndicator = modal.querySelector("#loading-indicator");
    const errorMessageSpan = modal.querySelector("#error-message");
    const overlay = modal.querySelector(".custom-modal__overlay");
    const closeButtons = modal.querySelectorAll(".close-modal");

    const showLoading = () => loadingIndicator.classList.add("is-visible");
    const hideLoading = () => loadingIndicator.classList.remove("is-visible");
    const showError = (message) => {
        errorMessageSpan.textContent = message;
        errorMessageSpan.classList.add("is-visible");
    };
    const clearError = () => {
        errorMessageSpan.textContent = "";
        errorMessageSpan.classList.remove("is-visible");
    };

    const renderPlaceholder = (message) => {
        tableContainer.innerHTML = "";
        const placeholder = document.createElement("p");
        placeholder.className = "registry-table__placeholder";
        placeholder.textContent = message;
        tableContainer.appendChild(placeholder);
    };

    const focusableSelectors = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

    const getFocusableElements = () =>
        Array.from(modalPanel.querySelectorAll(focusableSelectors))
            .filter(el => !el.hasAttribute("disabled") && el.getAttribute("tabindex") !== "-1");

    function trapFocus(event) {
        const focusableItems = getFocusableElements();
        if (event.key !== "Tab" || focusableItems.length === 0) {
            return;
        }

        const firstElement = focusableItems[0];
        const lastElement = focusableItems[focusableItems.length - 1];

        if (event.shiftKey) {
            if (document.activeElement === firstElement) {
                event.preventDefault();
                lastElement.focus();
            }
        } else if (document.activeElement === lastElement) {
            event.preventDefault();
            firstElement.focus();
        }
    }

    function closeModal() {
        modal.classList.remove("is-open");
        document.removeEventListener("keydown", handleKeydown);
        setTimeout(() => modal.remove(), 220);
    }

    function handleKeydown(event) {
        if (event.key === "Escape") {
            closeModal();
        } else {
            trapFocus(event);
        }
    }

    closeButtons.forEach(button => button.addEventListener("click", closeModal));
    overlay.addEventListener("click", closeModal);
    document.addEventListener("keydown", handleKeydown);

    requestAnimationFrame(() => modal.classList.add("is-open"));
    setTimeout(() => jkSelect.focus(), 200);

    // --- Функция удаления договора ---
    function handleDeleteContract(jkName, contractNumber, buttonElement) {
        if (!confirm(`Вы уверены, что хотите удалить договор ${contractNumber} из реестра ${jkName}? Это действие необратимо.`)) {
            return;
        }

        buttonElement.disabled = true;
        buttonElement.classList.add("is-loading");
        clearError();

        const deleteUrl = `/excel/delete-contract-from-registry?jkName=${encodeURIComponent(jkName)}&contractNumber=${encodeURIComponent(contractNumber)}`;

        fetch(deleteUrl, { method: "DELETE" })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(err.detail || `Ошибка ${response.status}: Не удалось удалить договор`);
                    });
                }
                return response.json();
            })
            .then(data => {
                alert(data.message || "Договор успешно удален.");
                loadRegistry(jkName);
            })
            .catch(error => {
                console.error("Ошибка при удалении:", error);
                showError(`Ошибка удаления: ${error.message}`);
                buttonElement.disabled = false;
                buttonElement.classList.remove("is-loading");
            });
    }

    // --- Функция загрузки данных реестра ---
    function loadRegistry(jkName) {
        renderPlaceholder("Загрузка данных…");
        showLoading();
        clearError();
        downloadButton.disabled = true;

        fetch(`/excel/get-contract-registry?jkName=${encodeURIComponent(jkName)}`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(err.detail || `Ошибка ${response.status}: Не удалось загрузить реестр`);
                    });
                }
                return response.json();
            })
            .then(data => {
                hideLoading();

                if (!data.registry || data.registry.length === 0) {
                    renderPlaceholder("Реестр пуст или не найден.");
                    downloadButton.disabled = true;
                    return;
                }

                const table = document.createElement("table");
                table.className = "registry-table";

                const thead = document.createElement("thead");
                thead.className = "registry-table__head";
                const headerRow = document.createElement("tr");
                headerRow.className = "registry-table__row registry-table__row--head";

                const headers = Object.keys(data.registry[0]);

                headers.forEach(header => {
                    const th = document.createElement("th");
                    th.className = "registry-table__cell registry-table__cell--head";
                    th.textContent = header;
                    headerRow.appendChild(th);
                });

                const thAction = document.createElement("th");
                thAction.className = "registry-table__cell registry-table__cell--head registry-table__cell--actions";
                thAction.textContent = "Действия";
                headerRow.appendChild(thAction);

                thead.appendChild(headerRow);
                table.appendChild(thead);

                const tbody = document.createElement("tbody");
                tbody.className = "registry-table__body";

                data.registry.forEach(row => {
                    const tr = document.createElement("tr");
                    tr.className = "registry-table__row";
                    const contractNumber = row["№ Договора"];

                    headers.forEach(header => {
                        const td = document.createElement("td");
                        td.className = "registry-table__cell";
                        const value = row[header];
                        td.textContent = value !== null && value !== undefined ? value : "";
                        tr.appendChild(td);
                    });

                    const tdAction = document.createElement("td");
                    tdAction.className = "registry-table__cell registry-table__cell--actions";

                    if (contractNumber) {
                        const deleteButton = document.createElement("button");
                        deleteButton.type = "button";
                        deleteButton.className = "registry-table__delete";
                        deleteButton.innerHTML = `
                            <svg viewBox="0 0 24 24" aria-hidden="true">
                                <path d="M9 3a1 1 0 0 0-1 1v1H5a1 1 0 0 0 0 2h14a1 1 0 1 0 0-2h-3V4a1 1 0 0 0-1-1H9Zm1 4v11a1 1 0 1 0 2 0V7h-2Zm-4 0v11a3 3 0 0 0 3 3h6a3 3 0 0 0 3-3V7h-2v11a1 1 0 1 1-2 0V7h-2v11a1 1 0 1 1-2 0V7H6Z"></path>
                            </svg>
                            <span>Удалить</span>
                        `;
                        deleteButton.addEventListener("click", () => handleDeleteContract(jkName, contractNumber, deleteButton));
                        tdAction.appendChild(deleteButton);
                    } else {
                        tdAction.textContent = "—";
                    }

                    tr.appendChild(tdAction);
                    tbody.appendChild(tr);
                });

                table.appendChild(tbody);

                const scrollContainer = document.createElement("div");
                scrollContainer.className = "registry-table__scroll";
                scrollContainer.appendChild(table);

                tableContainer.innerHTML = "";
                tableContainer.appendChild(scrollContainer);
                downloadButton.disabled = false;

                downloadButton.onclick = () => {
                    const downloadUrl = `/excel/download-contract-registry?jkName=${encodeURIComponent(jkName)}`;
                    const link = document.createElement("a");
                    link.href = downloadUrl;
                    link.download = `contract_registry_${jkName}.xlsx`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                };
            })
            .catch(error => {
                console.error("Ошибка загрузки реестра:", error);
                hideLoading();
                renderPlaceholder("Не удалось загрузить данные реестра.");
                showError(`Ошибка загрузки: ${error.message}`);
                downloadButton.disabled = true;
            });
    }

    const initialJk = jkSelect.value;
    if (initialJk) {
        loadRegistry(initialJk);
    }

    jkSelect.addEventListener("change", (event) => {
        loadRegistry(event.target.value);
    });
}
