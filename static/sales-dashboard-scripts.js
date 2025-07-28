"use strict";





let currentUser = null;

async function loadLeads() {
    try {
        // Получаем текущего пользователя
        const currentUser = await getCurrentUser();
        if (!currentUser) throw new Error("Пользователь не найден");

        // Запрашиваем лиды пользователя
        const response = await fetch(`/api/leads/user/${currentUser.id}?include_callbacks=true`);
        if (!response.ok) throw new Error("Ошибка загрузки данных");

        const leads = await response.json();

        // Очищаем старые данные в колонках
        document.querySelectorAll(".lead-list").forEach(el => el.innerHTML = "");

        // Группируем лидов по статусу
        const groupedLeads = leads.reduce((acc, lead) => {
            const status = lead.status; // Убедись, что API возвращает статус именно так
            if (!acc[status]) acc[status] = [];
            acc[status].push(lead);
            return acc;
        }, {});

        // Заполняем колонки
        Object.entries(groupedLeads).forEach(([status, leads]) => updateColumn(status, leads));

    } catch (error) {
        console.error("Ошибка загрузки лидов:", error);
    }
}

async function getCurrentUser() {
    try {
        const response = await fetch('/user/me');
        if (!response.ok) throw new Error("Ошибка загрузки пользователя");
        return await response.json();
    } catch (error) {
        console.error('Ошибка при получении текущего пользователя:', error);
        return null;
    }
}

function updateColumn(status, leads) {
    const column = document.querySelector(`.column[data-status="${status}"] .lead-list`);
    const leadCount = document.querySelector(`.column[data-status="${status}"] .lead-count`);

    if (!column) {
        console.warn(`Колонка для статуса "${status}" не найдена.`);
        return;
    }
    console.log("Updating column:", status, leads);

    // Очищаем список перед обновлением
    column.innerHTML = '';

    // Обновляем счётчик лидов
    leadCount.textContent = `${leads.length} ${getLeadWord(leads.length)}`;
    leads.sort((a, b) => {
        const aLatestCallback = a.callbacks.length ? new Date(Math.max(...a.callbacks.map(cb => new Date(cb)))) : null;
        const bLatestCallback = b.callbacks.length ? new Date(Math.max(...b.callbacks.map(cb => new Date(cb)))) : null;
        const aHasPending = aLatestCallback && aLatestCallback > new Date();
        const bHasPending = bLatestCallback && bLatestCallback > new Date();
        return bHasPending - aHasPending;
    });

    leads.forEach(lead => {
        const card = document.createElement("div");
        card.classList.add("card");
        card.setAttribute('draggable', true); // Включаем возможность перетаскивания
        card.setAttribute('data-lead-id', lead.id); // Добавляем ID лида для идентификации
        card.setAttribute('data-status', lead.status); // Текущий статус лида

        const now = new Date();
        const latestCallback = lead.callbacks.length ? new Date(Math.max(...lead.callbacks.map(cb => new Date(cb)))) : null;
        const isPending = latestCallback && latestCallback > now;
        const isMissed = latestCallback && latestCallback < now;
        if (isPending) card.style.border = '2px solid rgb(255 158 68)'; // Red border for pending
        if (isMissed) card.style.opacity = '0.5';
        if (isMissed) card.style.border = '4px solid #ff4444'

        card.innerHTML = `
                    <div class="card-header">
                        <div class="name">${lead.full_name || "Без имени"}</div>
                        <div class="date">${formatDate(lead.created_at)}</div>
                    </div>
                    <div class="contact-info">
                        <span class="messenger elements-info ${lead.contact_source}">${lead.contact_source || "Не указан"}</span>
                        <span class="location elements-info">${lead.region || "Не указан"}</span>
                        <span class="phone elements-info">${lead.phone || "Нет телефона"}</span>
                    </div>
                    <div class="payment-info">Вид оплаты: ${lead.payment_type || "Не указан"}</div>
                    <div class="payment-info">Предварительная сумма: ${lead.total_price?.toLocaleString() || "0"} ${lead.currency || ""}</div>
                    <div class="status">
                        <div class="status-indicator">
                            <span class="status-dot" style="background-color: ${getStatusColor(lead.state)};"></span>
                            <span>${getStatusText(lead.state)}</span>
                        </div>

                        <a href="/dashboard/sales/lead/${lead.id}" class="open-card">Открыть карточку</a>
                    </div>
                        ${latestCallback ? `<div>Напоминание: ${formatDate(latestCallback)}</div>` : ''} 

                `;

        // Добавляем обработчики для перетаскивания
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragend', handleDragEnd);

        column.appendChild(card);
    });
}

// Обработчики событий для drag-and-drop
let draggedLead = null;

function handleDragStart(e) {
    draggedLead = e.target;
    e.dataTransfer.setData('text/plain', draggedLead.getAttribute('data-lead-id')); // Передаём ID лида
    setTimeout(() => {
        draggedLead.style.opacity = '0.5'; // Скрываем элемент во время перетаскивания
    }, 0);
}

function handleDragEnd(e) {
    draggedLead.style.opacity = '1'; // Возвращаем видимость после перетаскивания
    draggedLead = null;
}

// Обработчики для колонок (drop zones)
document.querySelectorAll('.column').forEach(column => {
    column.addEventListener('dragover', (e) => {
        e.preventDefault(); // Позволяем сбрасывать элементы
        column.classList.add('drag-over'); // Добавляем класс для стилизации при наведении
    });

    column.addEventListener('dragleave', (e) => {
        column.classList.remove('drag-over'); // Убираем класс при уходе
    });

    column.addEventListener('drop', async (e) => {
        e.preventDefault();
        const leadId = e.dataTransfer.getData('text/plain');
        const newStatus = column.getAttribute('data-status');
        const currentStatus = draggedLead ? draggedLead.getAttribute('data-status') : null;

        if (currentStatus === newStatus) {
            showNotification("Нельзя перетаскивать лид в ту же колонку!", "error");
            return;
        }

        // const validTransitions = {
        //     COLD: ['WARM'], // Холодный -> Тёплый
        //     WARM: ['HOT'],  // Тёплый -> Горячий
        //     HOT: []        // Горячий -> никуда (нельзя возвращаться назад)
        // };

        

        if (!leadId || !newStatus) return;
        console.log(`Перетаскиваем лид ${leadId} в колонку ${newStatus}`);
        // Данные для обновления статуса лида
        const leadUpdateData = {
            status: newStatus,
            state: "PROCESSED" // Новый статус (COLD, WARM, HOT)
        };

        try {
            const response = await fetch(`/api/leads/${leadId}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(leadUpdateData),
            });

            const result = await response.json();
            if (response.ok) {
                showNotification(`Статус лида успешно обновлён на '${getStatusText1(newStatus)}'!`, "success");

                // Обновляем интерфейс: перетаскиваем лид в новую колонку
                const leadCard = document.querySelector(`.card[data-lead-id="${leadId}"]`);
                if (leadCard) {
                    leadCard.setAttribute('data-status', newStatus); // Обновляем статус в карточке


                    // Перемещаем карточку в новую колонку
                    const newColumn = document.querySelector(`.column[data-status="${newStatus}"] .lead-list`);
                    newColumn.appendChild(leadCard);
                    leadCard.classList.add('animate-drop'); // Добавляем класс для анимации

                    // Убираем анимацию после завершения
                    setTimeout(() => {
                        leadCard.classList.remove('animate-drop');
                    }, 500);

                    // Обновляем счётчики лидов в старой и новой колонках
                    updateLeadCounts();
                }
            } else {
                console.error("Ошибка при обновлении лида:", result);
                showNotification("Ошибка: " + (result.detail || "Не удалось обновить статус лида"), "error");
            }
        } catch (error) {
            console.error("Ошибка сети:", error);
            showNotification("Ошибка сети! Проверьте подключение к серверу.", "error");
        }
        column.classList.remove('drag-over');
    });
});

// Функция для выбора правильного склонения слова "лид"
function getLeadWord(count) {
    if (count % 10 === 1 && count % 100 !== 11) return "лид";
    if ([2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100)) return "лида";
    return "лидов";
}

// Функция для форматирования даты
function formatDate(dateString) {
    if (!dateString) return "Нет данных";
    return new Date(dateString).toLocaleDateString("ru-RU");
}

// Функция для подбора цвета статуса
function getStatusColor(state) {
    const colors = {
        'PROCESSED': '#00FF55',
        'IN_WORK': '#FFA500',
        'NEW': '#0088FF',
        'CLOSED': '#FF0000'
    };
    return colors[state] || '#CCCCCC';
}
function updateLeadCounts() {
    document.querySelectorAll('.column').forEach(column => {
        const leads = column.querySelectorAll('.card').length;
        const leadCount = column.querySelector('.lead-count');
        if (leadCount) {
            leadCount.textContent = `${leads} ${getLeadWord(leads)}`;
        }
    });
}
function getStatusText1(state) {
    const texts = {
        'HOT': 'Горячий',
        'WARM': 'Тёплый',
        'COLD': 'Холодный'
    };
    return texts[state] || state;
}
function getStatusText(state) {
    const texts = {
        'PROCESSED': 'Обработано',
        'IN_WORK': 'В обработке',
        'NEW': 'Новый',
        'CLOSED': 'Закрыт'
    };
    return texts[state] || state;
}


// Загружаем данные при открытии страницы
document.addEventListener("DOMContentLoaded", loadLeads);
