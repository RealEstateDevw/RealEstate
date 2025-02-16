"use strict";


document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');

console.log('Элемент найден:', searchInput); 
// Обработчик ввода текста
searchInput.addEventListener('input', async () => {
    const query = searchInput.value.trim();

    if (query === '') {
        searchResults.style.display = 'none';
        return;
    }

    try {
        const response = await fetch(`/api/mop/search?query=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error('Ошибка при получении данных');
        }

        const results = await response.json();
        displayResults(results);
    } catch (error) {
        console.error('Ошибка при поиске:', error);
        searchResults.innerHTML = '<div class="no-results">Произошла ошибка при загрузке данных</div>';
        searchResults.style.display = 'block';
    }
});
});

function displayResults(results) {
    const searchResults = document.getElementById('searchResults');
    searchResults.innerHTML = '';  // Очищаем список результатов

    if (results.length === 0) {
        searchResults.innerHTML = '<div class="no-results">Нет результатов</div>';
        searchResults.style.display = 'block';
    } else {
        results.forEach(result => {
            console.log(result);
            const item = document.createElement('div');
            item.classList.add('result-item');
            const role = result.role === 'salesperson' ? 'Продажник' : 'Лид';
            const role_icon = result.role === 'salesperson' ? '<i class="fas fa-user-tie"></i>' : '  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"> <path fill-rule="evenodd" clip-rule="evenodd" d="M10 4H14C17.7712 4 19.6569 4 20.8284 5.17157C22 6.34315 22 8.22876 22 12C22 15.7712 22 17.6569 20.8284 18.8284C19.6569 20 17.7712 20 14 20H10C6.22876 20 4.34315 20 3.17157 18.8284C2 17.6569 2 15.7712 2 12C2 8.22876 2 6.34315 3.17157 5.17157C4.34315 4 6.22876 4 10 4ZM13.25 9C13.25 8.58579 13.5858 8.25 14 8.25H19C19.4142 8.25 19.75 8.58579 19.75 9C19.75 9.41421 19.4142 9.75 19 9.75H14C13.5858 9.75 13.25 9.41421 13.25 9ZM14.25 12C14.25 11.5858 14.5858 11.25 15 11.25H19C19.4142 11.25 19.75 11.5858 19.75 12C19.75 12.4142 19.4142 12.75 19 12.75H15C14.5858 12.75 14.25 12.4142 14.25 12ZM15.25 15C15.25 14.5858 15.5858 14.25 16 14.25H19C19.4142 14.25 19.75 14.5858 19.75 15C19.75 15.4142 19.4142 15.75 19 15.75H16C15.5858 15.75 15.25 15.4142 15.25 15ZM11 9C11 10.1046 10.1046 11 9 11C7.89543 11 7 10.1046 7 9C7 7.89543 7.89543 7 9 7C10.1046 7 11 7.89543 11 9ZM9 17C13 17 13 16.1046 13 15C13 13.8954 11.2091 13 9 13C6.79086 13 5 13.8954 5 15C5 16.1046 5 17 9 17Z" fill="#216BF4"/> </svg>';


            item.innerHTML = `
                <div class="result-name">${result.full_name}</div>
                <div class="result-role">
                    ${role_icon}
                    ${role}
                </div>
            `;

            // Обработчик клика на элемент
            item.addEventListener('click', () => {
                console.log(`Вы выбрали: ${result.name}`);
            });

            searchResults.appendChild(item);
        });
        searchResults.style.display = 'block';
    }
};



let currentUser = null;

        async function loadLeads() {
            try {
                // Получаем текущего пользователя
                const currentUser = await getCurrentUser();
                if (!currentUser) throw new Error("Пользователь не найден");
        
                // Запрашиваем лиды пользователя
                const response = await fetch(`/api/leads/`);
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
        
            // Обновляем счётчик лидов
            leadCount.textContent = `${leads.length} ${getLeadWord(leads.length)}`;
        
            leads.forEach(lead => {
                const card = document.createElement("div");
                card.classList.add("card");
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
                        <a href="/dashboard/lead/${lead.id}" class="open-card">Открыть карточку</a>
                    </div>
                `;
                column.appendChild(card);
            });
        }
        
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
        function getStatusColor(status) {
            const colors = {
                "COLD": "#00A8E8",
                "WARM": "#FFB400",
                "HOT": "#FF5733",
                "POSTPONED": "orange",
                "IN_PROCESSING": "blue",
                "IN_WORK": "purple",
                "SENT": "green",
                "WAITING_RESPONSE": "yellow",
                "DECLINED": "red"
            };
            return colors[status] || "gray";
        }
        
        // Функция для перевода статусов на русский
        function getStatusText(status) {
            const translations = {
                "COLD": "Холодный",
                "WARM": "Тёплый",
                "HOT": "Горячий",
                "POSTPONED": "Отложено",
                "IN_PROCESSING": "В обработке",
                "IN_WORK": "В работе",
                "SENT": "Отправлено",
                "WAITING_RESPONSE": "Ожидание ответа",
                "DECLINED": "Отклонено"
            };
            return translations[status] || "Неизвестный статус";
        }
// Загружаем данные при открытии страницы
document.addEventListener("DOMContentLoaded", loadLeads);
