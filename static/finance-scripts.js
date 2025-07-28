"use strict";
function showSection(sectionId, element) {
    let parent = element.closest('.column');
    let tabs = parent.querySelectorAll('.tab');
    let sections = parent.querySelectorAll('.section');

    tabs.forEach(tab => tab.classList.remove('active'));
    sections.forEach(section => section.classList.remove('active'));

    element.classList.add('active');
    document.getElementById(sectionId).classList.add('active');
}


    async function fetchFinanceStats() {
        try {
            const response = await fetch("/api/finance/stats", {
                method: "GET",
                credentials: "include" // Указываем, чтобы браузер отправлял cookies с запросом
            });
            const stats = await response.json();
            if (response.ok) {
                // Обновляем данные в DOM
                document.getElementById("overduePayments").textContent = stats.overdue_payments;
                document.getElementById("previousOverdue").textContent = `${stats.previous_overdue_payments} за предыдущий месяц`;
                document.getElementById("timelyPayments").textContent = stats.timely_payments;
                document.getElementById("previousTimely").textContent = `${stats.previous_timely_payments} за предыдущий месяц`;
            } else {
                showNotification("Ошибка: " + (stats.detail || "Не удалось загрузить статистику"), "error");
            }
        } catch (error) {
            console.error("Ошибка сети:", error);

        }
    }
    async function fetchLeadStatuses() {
        try {
            const response = await fetch("/api/finance/statuses");
            const statuses = await response.json();
            if (response.ok) {
                // Обновляем закрытые лиды
                updateColumn("SALES", statuses.closed_leads, "closedLeads", "lead-count");
    
                // Обновляем лиды на выплате
                updateColumn("for-payment", statuses.leads_for_payment, "leads-payment", null, "Нет лидов на выплате");
                updateColumn("for-payment", statuses.purchases_for_payment, "purchases-payment", null, "Нет закупок на выплате");
    
                // Обновляем выплаченные
                updateColumn("paid", statuses.paid_leads, "leads-paid", null, "Нет выплаченных лидов");
                updateColumn("paid", statuses.paid_purchases, "purchases-paid", null, "Нет выплаченных закупок");
            } else {
                showNotification("Ошибка: " + (statuses.detail || "Не удалось загрузить статусы"), "error");
            }
        } catch (error) {
            console.error("Ошибка сети:", error);
            showNotification("Ошибка сети! Проверьте подключение к серверу.", "error");
        }
    }
    
    // Функция для обновления колонок
    function updateColumn(status, items, containerId, countId, defaultMessage = "Нет данных.") {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Контейнер с ID ${containerId} не найден`);
            return;
        }
    
        if (items.length === 0) {
            container.innerHTML = `<p>${defaultMessage}</p>`;
        } else {
            console.log(items);
            container.innerHTML = items.map(item => {
                // Определяем тип данных: лиды или закупки
                const isLead = containerId.includes("leads");
                const isPurchase = containerId.includes("purchases");
    
                if (isLead) {
                    // Генерация HTML для лидов
                    return `
                        <div class="card">
                            <div class="card-header">
                                <div class="name">${item.full_name || item.title || "Без названия"}</div>
                                <div class="date">${formatDate(item.created_at)}</div>
                            </div>
                            <hr class="divider">
                            <div class="contact-info">
                                <span class="messenger elements-info ${item.contact_source}">${item.contact_source}</span>
                                <span class="location elements-info">${item.region}</span>
                                <span class="phone elements-info">${item.phone}</span>
                            </div>
                            <hr class="divider">
                            <div class="payment-info">Вид оплаты: ${item.payment_type}</div>
                            <div class="payment-info">Предварительная сумма: ${item.total_price.toLocaleString()}</div>
                            <hr class="divider">
                            <div class="whose-lead">Ответственный менеджер: ${item.user.last_name} ${item.user.first_name}</div>
                            <hr class="divider">
                            <div class="status">
                                <div class="status-indicator">
                                    <span class="status-dot" style="background-color: ${getStatusColor(status)}"></span>
                                    <span>${status === "for-payment" ? "Ожидает оплаты" : status === "paid" ? "Выплачено" : "Закрыто"}</span>
                                </div>
                                <a href="/dashboard/sales/lead/${item.id}" class="open-card">Открыть карточку</a>
                            </div>
                        </div>
                    `;
                } else if (isPurchase) {
                    // Генерация HTML для закупок
                    return `
                        <div class="card">
                            <div class="card-header">
                                <div class="name">${item.title || "Без названия"}</div>
                                <div class="date">${formatDate(item.created_at)}</div>
                            </div>
                            <hr class="divider">
                            <div class="payment-info">Описание: ${item.description || "Нет описания"}</div>
                            <hr class="divider">
                            <div class="status">
                                <div class="status-indicator">
                                    <span class="status-dot" style="background-color: ${getStatusColor(status)}"></span>
                                    <span>${status === "for-payment" ? "Ожидает оплаты" : status === "paid" ? "Выплачено" : "Закрыто"}</span>
                                </div>
                                <span>Сумма: ${item.amount.toLocaleString()} сум</span>
                            </div>
                        </div>
                    `;
                } else {
                    // Если тип данных не определен, выводим сообщение об ошибке
                    console.error(`Неизвестный тип данных для контейнера с ID ${containerId}`);
                    return '';
                }
            }).join('');
        }
        
      
        // Обновляем счётчик, если указан
        if (countId) {
            const countElement = document.querySelector(`.column[data-status="${status}"] .lead-count`);
            if (countElement) {
                countElement.textContent = `${items.length} ${getLeadWord(items.length)}`;
            }
        }
    }
    function formatDate(isoString) {
        const date = new Date(isoString);
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        return `${day}.${month}.${year}`;
    }
    
    
    function getStatusColor(status){
        const colors = {
            'for-payment': '#FFA500',
            'paid': '#00FF55'
        };
        return colors[status] || '#CCCCCC';
    }
    // Вспомогательная функция для правильного склонения слова "лид"
    function getLeadWord(count) {
        if (count % 10 === 1 && count % 100 !== 11) {
            return "лид";
        } else if ([2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100)) {
            return "лида";
        } else {
            return "лидов";
        }
    }
    
    // Загружаем статистику при загрузке страницы
    document.addEventListener("DOMContentLoaded", async function() {
        await fetchFinanceStats(); // Предполагается, что эта функция определена где-то еще
        await fetchLeadStatuses();
        
        // Добавляем обработчики для табов, если они еще не добавлены
        function showSection(sectionId, tabElement) {
            // Найти родительский элемент с вкладками
            const tabsContainer = tabElement.closest('.tabs');
            // Удалить класс active у всех вкладок
            tabsContainer.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            // Добавить класс active к нажатой вкладке
            tabElement.classList.add('active');
            
            // Найти родительский элемент с секциями
            const sectionsContainer = tabElement.closest('.column').querySelector('.lead-list');
            // Скрыть все секции
            sectionsContainer.querySelectorAll('.section').forEach(section => section.classList.remove('active'));
            // Показать выбранную секцию
            document.getElementById(sectionId).classList.add('active');
        }
        
        // Добавляем обработчики клика, если они работают не через onclick в HTML
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', function() {
                const sectionId = this.getAttribute('onclick').match(/showSection\('([^']+)'/)[1];
                showSection(sectionId, this);
            });
        });
    });

    