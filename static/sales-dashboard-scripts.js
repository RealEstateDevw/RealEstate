"use strict";





let currentUser = null;

async function loadLeads() {
    try {
        console.log("Начинаем загрузку лидов...");
        
        // Получаем текущего пользователя
        const currentUser = await getCurrentUser();
        if (!currentUser) throw new Error("Пользователь не найден");
        console.log("Пользователь найден:", currentUser);

        // Запрашиваем лиды пользователя
        const response = await fetch(`/api/leads/user/${currentUser.id}?include_callbacks=true`);
        if (!response.ok) throw new Error("Ошибка загрузки данных");
        console.log("Ответ от API получен");

        const leads = await response.json();
        console.log("Лиды загружены:", leads);

        // Очищаем старые данные в колонках
        document.querySelectorAll(".lead-list").forEach(el => el.innerHTML = "");
        console.log("Колонки очищены");

        // Группируем лидов по статусу
        const groupedLeads = leads.reduce((acc, lead) => {
            const status = lead.status; // Убедись, что API возвращает статус именно так
            if (!acc[status]) acc[status] = [];
            acc[status].push(lead);
            return acc;
        }, {});
        console.log("Лиды сгруппированы:", groupedLeads);

        // // Проверяем истекшие лимиты и показываем уведомления
        // try {
        //     checkCallLimits(leads);
        //     console.log("Проверка лимитов завершена");
        // } catch (error) {
        //     console.error("Ошибка при проверке лимитов:", error);
        // }

        // Заполняем колонки
        Object.entries(groupedLeads).forEach(([status, leads]) => {
            try {
                console.log(`Обновляем колонку ${status} с ${leads.length} лидами`);
                updateColumn(status, leads);
            } catch (error) {
                console.error(`Ошибка при обновлении колонки ${status}:`, error);
            }
        });
        console.log("Все колонки обновлены");

    } catch (error) {
        console.error("Ошибка загрузки лидов:", error);
        showNotification("Ошибка загрузки данных: " + error.message, "error");
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
    console.log(`Обновляем колонку ${status} с ${leads.length} лидами`);
    
    const column = document.querySelector(`.column[data-status="${status}"] .lead-list`);
    const leadCount = document.querySelector(`.column[data-status="${status}"] .lead-count`);

    if (!column) {
        console.error(`Колонка для статуса "${status}" не найдена.`);
        return;
    }
    
    console.log("Колонка найдена, начинаем обновление");

    // Очищаем список перед обновлением
    column.innerHTML = '';

    // Обновляем счётчик лидов
    leadCount.textContent = `${leads.length} ${getLeadWord(leads.length)}`;
    // leads.sort((a, b) => {
    //     // Приоритет 1: Карточки с истекшим лимитом созвона (24 часа)
    //     const aCallLimitExpired = isCallLimitExpired(a);
    //     const bCallLimitExpired = isCallLimitExpired(b);
        
    //     if (aCallLimitExpired && !bCallLimitExpired) return -1;
    //     if (!aCallLimitExpired && bCallLimitExpired) return 1;
        
    //     // Приоритет 2: Карточки с предстоящими созвонами
    //     const aLatestCallback = a.callbacks.length ? new Date(Math.max(...a.callbacks.map(cb => new Date(cb)))) : null;
    //     const bLatestCallback = b.callbacks.length ? new Date(Math.max(...b.callbacks.map(cb => new Date(cb)))) : null;
    //     const aHasPending = aLatestCallback && aLatestCallback > new Date();
    //     const bHasPending = bLatestCallback && bLatestCallback > new Date();
        
    //     if (aCallLimitExpired && bCallLimitExpired) {
    //         // Если у обеих истек лимит, сортируем по времени истечения
    //         const aExpiredTime = getCallLimitExpiredTime(a);
    //         const bExpiredTime = getCallLimitExpiredTime(b);
    //         return aExpiredTime - bExpiredTime;
    //     }
        
    //     return bHasPending - aHasPending;
    // });

    leads.forEach((lead, index) => {
        try {
            console.log(`Создаем карточку для лида ${index + 1}/${leads.length}:`, lead.full_name);
            
            const card = document.createElement("div");
            card.classList.add("card");
            card.setAttribute('draggable', true); // Включаем возможность перетаскивания
            card.setAttribute('data-lead-id', lead.id); // Добавляем ID лида для идентификации
            card.setAttribute('data-status', lead.status); // Текущий статус лида
            
        const now = new Date();
        const latestCallback = lead.callbacks.length ? new Date(Math.max(...lead.callbacks.map(cb => new Date(cb)))) : null;
        const isPending = latestCallback && latestCallback > now;
        const isMissed = latestCallback && latestCallback < now;
        // const isCallLimitExpiredFlag = isCallLimitExpired(lead);
        
        // Добавляем класс для лидов без доступа только если есть проблемы с callback
        if ( isMissed) {
            card.classList.add("no-access-card");
        }
        
        // Проверяем, был ли callback сегодня (карточка обработана)
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const callbackDate = latestCallback ? new Date(latestCallback) : null;
        if (callbackDate) {
            callbackDate.setHours(0, 0, 0, 0);
        }
        const isProcessedToday = latestCallback && callbackDate && callbackDate.getTime() === today.getTime();
        
        // Стили для разных состояний
        if (isProcessedToday) {
            // Карточка обработана сегодня (есть callback сегодня)
            card.style.border = '2px solid #10b981'; // Зеленая рамка
            card.style.backgroundColor = '#f0fdf4'; // Светло-зеленый фон
            card.classList.add('call-completed');
        // } else if (isCallLimitExpiredFlag) {
        //     // Лимит истек (callback был вчера или раньше) - ВЫСОКИЙ ПРИОРИТЕТ
        //     card.style.border = '4px solid #ff0000'; // Красная рамка для истекшего лимита
        //     card.style.backgroundColor = '#fff5f5'; // Светло-красный фон
        //     card.classList.add('call-limit-expired');
        } else if (isPending) {
            // Предстоящий callback - СРЕДНИЙ ПРИОРИТЕТ
            card.style.border = '2px solid rgb(255 158 68)'; // Оранжевая рамка для предстоящих
        } else if (isMissed) {
            // Пропущенный callback - ВЫСОКИЙ ПРИОРИТЕТ
            card.style.border = '4px solid #ff4444';
        } else {
            // Нет callback - ОБЫЧНАЯ КАРТОЧКА (есть доступ)
            card.style.border = '1px solid #e5e7eb';
            card.style.backgroundColor = '#ffffff';
        }

        // Создаем индикатор истекшего лимита
        // const callLimitIndicator = isCallLimitExpiredFlag ? 
        //     `<div class="call-limit-warning" style="background: #ff0000; color: white; padding: 8px; margin: 8px 0; border-radius: 8px; text-align: center; font-weight: bold; animation: pulse 2s infinite;">
        //         ⚠️ ЛИМИТ СОЗВОНА ИСТЕК! Требуется срочное действие
        //     </div>` : '';

        // Создаем индикатор времени до истечения лимита
        // const timeUntilExpiry = getTimeUntilCallLimitExpires(lead);
        // const timeWarning = timeUntilExpiry && timeUntilExpiry < 2 * 60 * 60 * 1000 ? // Менее 2 часов
        //     `<div class="time-warning" style="background: #ffa500; color: white; padding: 6px; margin: 6px 0; border-radius: 6px; text-align: center; font-size: 0.9em;">
        //         ⏰ Лимит созвона истечет через ${Math.round(timeUntilExpiry / (60 * 60 * 1000))}ч ${Math.round((timeUntilExpiry % (60 * 60 * 1000)) / (60 * 1000))}м
        //     </div>` : '';

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

                        ${isProcessedToday ? 
                            `<a href="/dashboard/sales/lead/${lead.id}" class="open-card processed-card">Карточка обработана</a>` :
                            `<a href="/dashboard/sales/lead/${lead.id}" class="open-card">Открыть карточку</a>`
                        }
                    </div>
                        ${latestCallback && !isProcessedToday ? `<div>Напоминание: ${formatDate(latestCallback)}</div>` : ''} 

                `;

            // Добавляем обработчики для перетаскивания
            card.addEventListener('dragstart', handleDragStart);
            card.addEventListener('dragend', handleDragEnd);

            column.appendChild(card);
            console.log(`Карточка для лида ${lead.full_name} добавлена`);
            
        } catch (error) {
            console.error(`Ошибка при создании карточки для лида ${lead.full_name}:`, error);
        }
    });
}

// Обработчики событий для drag-and-drop
let draggedLead = null;
let leadToDelete = null;

function handleDragStart(e) {
    draggedLead = e.target;
    e.dataTransfer.setData('text/plain', draggedLead.getAttribute('data-lead-id')); // Передаём ID лида
    setTimeout(() => {
        draggedLead.style.opacity = '0.5'; // Скрываем элемент во время перетаскивания
    }, 0);
    
    // Показываем кнопку удаления при начале перетаскивания
    showDeleteButton();
}

function handleDragEnd(e) {
    draggedLead.style.opacity = '1'; // Возвращаем видимость после перетаскивания
    draggedLead = null;
    
    // Скрываем кнопку удаления при окончании перетаскивания
    hideDeleteButton();
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

// // Функция для проверки истечения лимита созвона (24 часа)
// function isCallLimitExpired(lead) {
//     // Если у лида нет callbacks, лимит не применим
//     if (!lead.callbacks || lead.callbacks.length === 0) return false;
    
//     // Получаем последний callback
//     const latestCallback = new Date(Math.max(...lead.callbacks.map(cb => new Date(cb))));
//     const now = new Date();
    
//     // Если последний callback был в будущем (предстоящий), лимит не истек
//     if (latestCallback > now) return false;
    
//     // Проверяем, был ли callback сегодня - если да, то лимит не истек
//     const today = new Date();
//     today.setHours(0, 0, 0, 0);
//     const callbackDate = new Date(latestCallback);
//     callbackDate.setHours(0, 0, 0, 0);
    
//     if (callbackDate.getTime() === today.getTime()) {
//         return false; // Callback был сегодня, лимит не истек
//     }
    
//     // Проверяем, прошло ли 24 часа с последнего callback
//     const timeDiff = now - latestCallback;
//     const hoursDiff = timeDiff / (1000 * 60 * 60); // Конвертируем в часы
    
//     return hoursDiff >= 24;
// }

// // Функция для получения времени истечения лимита
// function getCallLimitExpiredTime(lead) {
//     if (!lead.callbacks || lead.callbacks.length === 0) return null;
    
//     const latestCallback = new Date(Math.max(...lead.callbacks.map(cb => new Date(cb))));
//     const expiredTime = new Date(latestCallback.getTime() + 24 * 60 * 60 * 1000); // +24 часа
    
//     return expiredTime;
// }

// // Функция для получения времени до истечения лимита
// function getTimeUntilCallLimitExpires(lead) {
//     if (!lead.callbacks || lead.callbacks.length === 0) return null;
    
//     const latestCallback = new Date(Math.max(...lead.callbacks.map(cb => new Date(cb))));
//     const expiredTime = new Date(latestCallback.getTime() + 24 * 60 * 60 * 1000);
//     const now = new Date();
    
//     if (expiredTime <= now) return null; // Уже истек
    
//     return expiredTime - now;
// }

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


// Функция для автоматического обновления данных
function startAutoRefresh() {
    // Обновляем данные каждые 5 минут
    setInterval(() => {
        console.log("Автоматическое обновление данных...");
        loadLeads();
    }, 5 * 60 * 1000); // 5 минут
}

// Функция для проверки и показа уведомлений о истекших лимитах
// function checkCallLimits(leads) {
//     const expiredLeads = leads.filter(lead => isCallLimitExpired(lead));
    
//     if (expiredLeads.length > 0) {
//         showNotification(
//             `Внимание! У ${expiredLeads.length} лид${expiredLeads.length === 1 ? 'а' : 'ов'} истек лимит созвона!`, 
//             "error"
//         );
//     }
// }

// Функции для работы с кнопкой удаления
function showDeleteButton() {
    const deleteZone = document.getElementById('delete-zone');
    if (deleteZone) {
        deleteZone.style.display = 'block';
    }
}

function hideDeleteButton() {
    const deleteZone = document.getElementById('delete-zone');
    if (deleteZone) {
        deleteZone.style.display = 'none';
    }
}

// Обработчик для кнопки удаления
document.addEventListener('DOMContentLoaded', () => {
    const deleteZone = document.getElementById('delete-zone');
    if (deleteZone) {
        deleteZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            deleteZone.classList.add('drag-over-delete');
        });
        
        deleteZone.addEventListener('dragleave', (e) => {
            deleteZone.classList.remove('drag-over-delete');
        });
        
        deleteZone.addEventListener('drop', (e) => {
            e.preventDefault();
            deleteZone.classList.remove('drag-over-delete');
            
            const leadId = e.dataTransfer.getData('text/plain');
            const leadCard = document.querySelector(`.card[data-lead-id="${leadId}"]`);
            
            if (leadCard) {
                const leadName = leadCard.querySelector('.name').textContent;
                showDeleteModal(leadId, leadName);
            }
        });
    }
});

// Функции для модального окна удаления
function showDeleteModal(leadId, leadName) {
    leadToDelete = leadId;
    const modal = document.getElementById('delete-modal');
    const leadNameElement = document.getElementById('delete-lead-name');
    
    if (modal && leadNameElement) {
        leadNameElement.textContent = leadName;
        modal.style.display = 'flex';
    }
}

function closeDeleteModal() {
    const modal = document.getElementById('delete-modal');
    if (modal) {
        modal.style.display = 'none';
        leadToDelete = null;
    }
}

async function confirmDelete() {
    if (!leadToDelete) return;
    
    try {
        const response = await fetch(`/api/leads/${leadToDelete}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            showNotification('Лид успешно удален!', 'success');
            
            // Удаляем карточку из DOM
            const leadCard = document.querySelector(`.card[data-lead-id="${leadToDelete}"]`);
            if (leadCard) {
                leadCard.remove();
                updateLeadCounts(); // Обновляем счетчики
            }
            
            closeDeleteModal();
        } else {
            const result = await response.json();
            showNotification('Ошибка при удалении лида: ' + (result.detail || 'Неизвестная ошибка'), 'error');
        }
    } catch (error) {
        console.error('Ошибка при удалении лида:', error);
        showNotification('Ошибка сети при удалении лида!', 'error');
    }
}

// Закрытие модального окна при клике вне его
document.addEventListener('click', (e) => {
    const modal = document.getElementById('delete-modal');
    if (modal && e.target === modal) {
        closeDeleteModal();
    }
});

// Закрытие модального окна по клавише Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeDeleteModal();
    }
});

// Загружаем данные при открытии страницы
document.addEventListener("DOMContentLoaded", () => {
    loadLeads();
    startAutoRefresh();
});
