
"use strict";

let employeesList = [];

async function fetchEmployees() {
  try {
    const response = await fetch('/api/users/employees?role_id=1');
    if (!response.ok) throw new Error('Ошибка загрузки продажников');
    employeesList = await response.json();
  } catch (err) {
    console.error('Ошибка при получении списка продажников:', err);
  }
}

async function assignLead(leadId) {
  const select = document.getElementById(`assign-user-${leadId}`);
  const userId = select.value;
  if (!userId) {
    showNotification('Пожалуйста, выберите продажника.', 'error');
    return;
  }
  try {
    const response = await fetch(`/api/leads/${leadId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: Number(userId) }),
    });
    if (!response.ok) throw new Error('Ошибка обновления лида');
    showNotification('Лид успешно привязан!');
    fetchUnassignedLeads();
  } catch (err) {
    console.error('Ошибка при привязке лида:', err);
    showNotification(err.message, 'error');
  }
}






let currentUser = null;

function showNotification(message, type = "success") {
    const notification = document.getElementById("notification");
    const notificationMessage = document.getElementById("notification-message");
    const closeBtn = document.getElementById("close-notification");

    // Устанавливаем текст уведомления
    notificationMessage.textContent = message;

    // Устанавливаем стиль в зависимости от типа (успех или ошибка)
    if (type === "success") {
        notification.style.backgroundColor = "#4CAF50"; // Зеленый для успеха
        notification.style.color = "white";
    } else {
        notification.style.backgroundColor = "#f44336"; // Красный для ошибки
        notification.style.color = "white";
    }

    // Показываем уведомление
    notification.style.display = "flex";
    notification.style.position = "fixed";
    notification.style.top = "20px";
    notification.style.left = "50%";
    notification.style.transform = "translateX(-50%)";
    notification.style.padding = "10px 20px";
    notification.style.borderRadius = "5px";
    notification.style.zIndex = "1000";
    notification.style.boxShadow = "0 4px 6px rgba(0, 0, 0, 0.1)";
    notification.style.transition = "opacity 0.5s";

    // Автоматически скрываем уведомление через 3 секунды
    setTimeout(() => {
        notification.style.opacity = "0";
        setTimeout(() => {
            notification.style.display = "none";
            notification.style.opacity = "1"; // Сбрасываем opacity для следующего показа
        }, 500);
    }, 3000);

    // Закрытие уведомления по клику на крестик
    closeBtn.addEventListener('click', () => {
        notification.style.opacity = "0";
        setTimeout(() => {
            notification.style.display = "none";
            notification.style.opacity = "1"; // Сбрасываем opacity для следующего показа
        }, 500);
    }, { once: true }); // Убираем слушатель после одного клика, чтобы избежать дублирования
}

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
                        <a href="/dashboard/sales/lead/${lead.id}" class="open-card">Открыть карточку</a>
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
                "SENT": "green",
                "WAITING_RESPONSE": "yellow",
                "DECLINED": "red",
                'PROCESSED': '#00FF55',
        'IN_WORK': '#FFA500',
        'NEW': '#0088FF',
        'CLOSED': '#FF0000'
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
                "DECLINED": "Отклонено",
                'PROCESSED': 'Обработано',
        'IN_PROGRESS': 'В обработке',
        'NEW': 'Новый',
        'CLOSED': 'Закрыт'
            };
            return translations[status] || "Неизвестный статус";
        }


function renderLeadCard(lead) {
    return `
      <div class="card">
        <div class="card-header">
          <div class="name">${lead.full_name}</div>
          <div class="date">${lead.date}</div>
        </div>
        <hr class="divider">
        <div class="contact-info">
          <span class="messenger elements-info ${lead.contact_source}">${lead.contact_source}</span>
          <span class="location elements-info">${lead.region}</span>
          <span class="phone elements-info">${lead.phone}</span>
        </div>
        <hr class="divider">
        <div class="payment-info">Вид оплаты: ${lead.payment_type}</div>
        <div class="payment-info">Сумма: ${lead.total_price.toLocaleString()}</div>
        <hr class="divider">
        <div class="status">
          <div class="status-indicator">
            <span class="status-dot" style="background-color: ${getStatusColor(lead.state)}"></span>
            <span>${getStatusText(lead.state)}</span>
          </div>
          <a href="/dashboard/sales/lead/${lead.id}" class="open-card">Открыть карточку</a>
        </div>
      </div>
    `;
}

function renderUnassignedLeadCard(lead) {
  const options = employeesList.map(user =>
    `<option value="${user.id}">${user.first_name} ${user.last_name}</option>`
  ).join('');
  return `
    <div class="card">
      <div class="card-header">
        <div class="name">${lead.full_name}</div>
        <div class="date">${lead.date}</div>
      </div>
      <hr class="divider">
      <div class="contact-info">
        <span class="messenger elements-info ${lead.contact_source}">${lead.contact_source}</span>
        <span class="location elements-info">${lead.region}</span>
        <span class="phone elements-info">${lead.phone}</span>
      </div>
      <hr class="divider">
      <div class="payment-info">Вид оплаты: ${lead.payment_type}</div>
      <div class="payment-info">Сумма: ${lead.total_price.toLocaleString()}</div>
      <hr class="divider">
      <div class="assign">
        <select id="assign-user-${lead.id}">
          <option value="">-- Выберите продажника --</option>
          ${options}
        </select>
        <button onclick="assignLead(${lead.id})">Привязать</button>
      </div>
    </div>
  `;
}


        

function toggleInactive() {
  const columns = document.querySelector('.columns');
  const section = document.querySelector('.lead-section');
  const container = document.getElementById('leads-container');
  const button = document.querySelector('.btn-irrelevant');
  const iconSvg = document.getElementById('icon-svg');
  // Toggle this button's active state
  const isActive = button.classList.toggle('active');
  // Deactivate the other button
  const unassignedBtn = document.querySelector('.btn-irrelevant-unsigned');
  if (unassignedBtn) unassignedBtn.classList.remove('active');
  // Reset the unassigned button icon to default
  const unassignedIcon = document.getElementById('icon-svg2');
  if (unassignedIcon) {
    unassignedIcon.innerHTML = '<path fill-rule="evenodd" clip-rule="evenodd" d="M4.47721 17.0383C3.66363 18.2935 3.99941 20.0388 4.67097 23.5293C5.1544 26.0421 5.39612 27.2984 6.23364 28.1321C6.45093 28.3485 6.69405 28.5403 6.95813 28.7036C7.97593 29.3332 9.32719 29.3332 12.0297 29.3332H21.3036C24.0061 29.3332 25.3575 29.3332 26.3752 28.7036C26.6393 28.5403 26.8824 28.3485 27.0997 28.1321C27.9372 27.2984 28.1789 26.0421 28.6624 23.5293C29.3339 20.0388 29.6697 18.2935 28.8561 17.0383C28.6485 16.7179 28.3924 16.428 28.0961 16.1776C26.9348 15.1967 25.0577 15.1967 21.3036 15.1967H12.0297C8.27556 15.1967 6.39851 15.1967 5.23723 16.1776C4.94088 16.428 4.68484 16.7179 4.47721 17.0383ZM12.9269 22.9075C12.9269 22.3752 13.3835 21.9436 13.9468 21.9436H19.3864C19.9496 21.9436 20.4063 22.3752 20.4063 22.9075C20.4063 23.4397 19.9496 23.8713 19.3864 23.8713H13.9468C13.3835 23.8713 12.9269 23.4397 12.9269 22.9075Z" fill="black"/>';
  }

  if (isActive) {
    // Show inactive leads
    columns.classList.add('inactive');
    section.classList.remove('inactive');
    fetchInactiveLeads();
    iconSvg.innerHTML = '<path fill-rule="evenodd" clip-rule="evenodd" d="M4.47721 17.0384C3.66363 18.2936 3.99941 20.0389 4.67097 23.5294C5.1544 26.0422 5.39612 27.2985 6.23364 28.1322C6.45093 28.3486 6.69405 28.5404 6.95813 28.7037C7.97593 29.3333 9.32719 29.3333 12.0297 29.3333H21.3036C24.0061 29.3333 25.3575 29.3333 26.3752 28.7037C26.6393 28.5404 26.8824 28.3486 27.0997 28.1322C27.9372 27.2985 28.1789 26.0422 28.6624 23.5294C29.3339 20.0389 29.6697 18.2936 28.8561 17.0384C28.6485 16.718 28.3924 16.4281 28.0961 16.1777C26.9348 15.1968 25.0577 15.1968 21.3036 15.1968H12.0297C8.27556 15.1968 6.39851 15.1968 5.23723 16.1777C4.94088 16.4281 4.68484 16.718 4.47721 17.0384ZM12.9269 22.9076C12.9269 22.3753 13.3835 21.9437 13.9468 21.9437H19.3864C19.9496 21.9437 20.4063 22.3753 20.4063 22.9076C20.4063 23.4398 19.9496 23.8714 19.3864 23.8714H13.9468C13.3835 23.8714 12.9269 23.4398 12.9269 22.9076Z" fill="white"/>';
  } else {
    // Return to default columns
    columns.classList.remove('inactive');
    section.classList.add('inactive');
    container.innerHTML = '';
    iconSvg.innerHTML = '<path fill-rule="evenodd" clip-rule="evenodd" d="M4.47721 17.0383C3.66363 18.2935 3.99941 20.0388 4.67097 23.5293C5.1544 26.0421 5.39612 27.2984 6.23364 28.1321C6.45093 28.3485 6.69405 28.5403 6.95813 28.7036C7.97593 29.3332 9.32719 29.3332 12.0297 29.3332H21.3036C24.0061 29.3332 25.3575 29.3332 26.3752 28.7036C26.6393 28.5403 26.8824 28.3485 27.0997 28.1321C27.9372 27.2984 28.1789 26.0421 28.6624 23.5293C29.3339 20.0388 29.6697 18.2935 28.8561 17.0383C28.6485 16.7179 28.3924 16.428 28.0961 16.1776C26.9348 15.1967 25.0577 15.1967 21.3036 15.1967H12.0297C8.27556 15.1967 6.39851 15.1967 5.23723 16.1776C4.94088 16.428 4.68484 16.7179 4.47721 17.0383ZM12.9269 22.9075C12.9269 22.3752 13.3835 21.9436 13.9468 21.9436H19.3864C19.9496 21.9436 20.4063 22.3752 20.4063 22.9075C20.4063 23.4397 19.9496 23.8713 19.3864 23.8713H13.9468C13.3835 23.8713 12.9269 23.4397 12.9269 22.9075Z" fill="black"/>';
  }
}

function toggleUnassigned() {
  const columns = document.querySelector('.columns');
  const section = document.querySelector('.lead-section');
  const container = document.getElementById('leads-container');
  const button = document.querySelector('.btn-irrelevant-unsigned');
  const iconSvg = document.getElementById('icon-svg2');
  const inactiveBtn = document.querySelector('.btn-irrelevant');
  // Toggle this button's active state
  const isActive = button.classList.toggle('active');
  // Deactivate the inactive button
  if (inactiveBtn) inactiveBtn.classList.remove('active');
  // Reset the inactive button icon to default
  const inactiveIcon = document.getElementById('icon-svg');
  if (inactiveIcon) {
    inactiveIcon.innerHTML = '<path fill-rule="evenodd" clip-rule="evenodd" d="M4.47721 17.0383C3.66363 18.2935 3.99941 20.0388 4.67097 23.5293C5.1544 26.0421 5.39612 27.2984 6.23364 28.1321C6.45093 28.3485 6.69405 28.5403 6.95813 28.7036C7.97593 29.3332 9.32719 29.3332 12.0297 29.3332H21.3036C24.0061 29.3332 25.3575 29.3332 26.3752 28.7036C26.6393 28.5403 26.8824 28.3485 27.0997 28.1321C27.9372 27.2984 28.1789 26.0421 28.6624 23.5293C29.3339 20.0388 29.6697 18.2935 28.8561 17.0383C28.6485 16.7179 28.3924 16.428 28.0961 16.1776C26.9348 15.1967 25.0577 15.1967 21.3036 15.1967H12.0297C8.27556 15.1967 6.39851 15.1967 5.23723 16.1776C4.94088 16.428 4.68484 16.7179 4.47721 17.0383ZM12.9269 22.9075C12.9269 22.3752 13.3835 21.9436 13.9468 21.9436H19.3864C19.9496 21.9436 20.4063 22.3752 20.4063 22.9075C20.4063 23.4397 19.9496 23.8713 19.3864 23.8713H13.9468C13.3835 23.8713 12.9269 23.4397 12.9269 22.9075Z" fill="black"/>';
  }

  if (isActive) {
    // Show unassigned leads
    columns.classList.add('inactive');
    section.classList.remove('inactive');
    fetchUnassignedLeads();
    iconSvg.innerHTML = '<path fill-rule="evenodd" clip-rule="evenodd" d="M4.47721 17.0384C3.66363 18.2936 3.99941 20.0389 4.67097 23.5294C5.1544 26.0422 5.39612 27.2985 6.23364 28.1322C6.45093 28.3486 6.69405 28.5404 6.95813 28.7037C7.97593 29.3333 9.32719 29.3333 12.0297 29.3333H21.3036C24.0061 29.3333 25.3575 29.3333 26.3752 28.7037C26.6393 28.5404 26.8824 28.3486 27.0997 28.1322C27.9372 27.2985 28.1789 26.0422 28.6624 23.5294C29.3339 20.0389 29.6697 18.2936 28.8561 17.0384C28.6485 16.718 28.3924 16.4281 28.0961 16.1777C26.9348 15.1968 25.0577 15.1968 21.3036 15.1968H12.0297C8.27556 15.1968 6.39851 15.1968 5.23723 16.1777C4.94088 16.4281 4.68484 16.718 4.47721 17.0384ZM12.9269 22.9076C12.9269 22.3753 13.3835 21.9437 13.9468 21.9437H19.3864C19.9496 21.9437 20.4063 22.3753 20.4063 22.9076C20.4063 23.4398 19.9496 23.8714 19.3864 23.8714H13.9468C13.3835 23.8714 12.9269 23.4398 12.9269 22.9076Z" fill="white"/>';
  } else {
    // Return to default columns
    columns.classList.remove('inactive');
    section.classList.add('inactive');
    container.innerHTML = '';
    iconSvg.innerHTML = '<path fill-rule="evenodd" clip-rule="evenodd" d="M4.47721 17.0383C3.66363 18.2935 3.99941 20.0388 4.67097 23.5293C5.1544 26.0421 5.39612 27.2984 6.23364 28.1321C6.45093 28.3485 6.69405 28.5403 6.95813 28.7036C7.97593 29.3332 9.32719 29.3332 12.0297 29.3332H21.3036C24.0061 29.3332 25.3575 29.3332 26.3752 28.7036C26.6393 28.5403 26.8824 28.3485 27.0997 28.1321C27.9372 27.2984 28.1789 26.0421 28.6624 23.5293C29.3339 20.0388 29.6697 18.2935 28.8561 17.0383C28.6485 16.7179 28.3924 16.428 28.0961 16.1776C26.9348 15.1967 25.0577 15.1967 21.3036 15.1967H12.0297C8.27556 15.1967 6.39851 15.1967 5.23723 16.1776C4.94088 16.428 4.68484 16.7179 4.47721 17.0383ZM12.9269 22.9075C12.9269 22.3752 13.3835 21.9436 13.9468 21.9436H19.3864C19.9496 21.9436 20.4063 22.3752 20.4063 22.9075C20.4063 23.4397 19.9496 23.8713 19.3864 23.8713H13.9468C13.3835 23.8713 12.9269 23.4397 12.9269 22.9075Z" fill="black"/>';
  }
}
        
// Загружаем данные при открытии страницы





async function fetchDailyStatistics() {
    try {
        const response = await fetch('/api/leads/lead-statistics/daily');
        const data = await response.json();
        
        // Update new leads statistics
        const newLeadsElement = document.querySelector('#new-leads-count');
        const newLeadsYesterdayElement = document.querySelector('#new-leads-yesterday');
        const newLeadsTrendIcon = document.querySelector('#new-leads-trend');
        
        newLeadsElement.textContent = data.new_leads.today;
        newLeadsYesterdayElement.textContent = `${data.new_leads.yesterday} за предыдущий день`;
        updateTrendIcon(newLeadsTrendIcon, data.new_leads.trend);
        
        // Update processed leads statistics
        const processedLeadsElement = document.querySelector('#processed-leads-count');
        const processedLeadsYesterdayElement = document.querySelector('#processed-leads-yesterday');
        const processedLeadsTrendIcon = document.querySelector('#processed-leads-trend');
        
        processedLeadsElement.textContent = data.processed_leads.today;
        processedLeadsYesterdayElement.textContent = `${data.processed_leads.yesterday} за предыдущий день`;
        updateTrendIcon(processedLeadsTrendIcon, data.processed_leads.trend);
    } catch (error) {
        console.error('Error fetching statistics:', error);
    }
}

function updateTrendIcon(element, trend) {
    if (trend === 'up') {
        element.innerHTML = `<path d="M29.3334 9.83334L19.4938 19.6129C18.1637 20.9351 17.4985 21.596 16.6735 21.596C15.8486 21.5959 15.1835 20.9347 13.8537 19.6123L13.5346 19.2949C12.2035 17.9713 11.5379 17.3095 10.7124 17.3099C9.88683 17.3101 9.22176 17.9724 7.89164 19.2969L2.66675 24.5M29.3334 9.83334V17.2277M29.3334 9.83334H21.8906" stroke="#00CC22" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;
    } else {
        element.innerHTML = `<path d="M29.3332 24.5L19.4936 14.7204C18.1634 13.3983 17.4982 12.7373 16.6733 12.7374C15.8484 12.7375 15.1833 13.3987 13.8534 14.7211L13.5344 15.0384C12.2032 16.362 11.5377 17.0239 10.7121 17.0235C9.88658 17.0232 9.22152 16.3609 7.8914 15.0364L2.6665 9.83334M29.3332 24.5V17.1056M29.3332 24.5H21.8904" stroke="#FF0000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;
    }
}

async function fetchInactiveLeads() {
    try {
      const response = await fetch('/api/leads/inactive');
      const data = await response.json();
      document.getElementById('lead-section-title').textContent =
        `Неактуальные ${data.total_count} ${getLeadWord(data.total_count)}`;
      const container = document.getElementById('leads-container');
      container.innerHTML = data.leads.map(renderLeadCard).join('');
    } catch (err) {
      console.error('Ошибка при загрузке неактуальных лидов', err);
    }
  }


async function fetchUnassignedLeads() {
    try {
      const response = await fetch('/api/leads/unassigned');
      const data = await response.json();
      document.getElementById('lead-section-title').textContent =
        `Неназначенные ${data.total_count} ${getLeadWord(data.total_count)}`;
      const container = document.getElementById('leads-container');
      container.innerHTML = data.leads.map(renderUnassignedLeadCard).join('');
    } catch (err) {
      console.error('Ошибка при загрузке неназначенных лидов', err);
    }
}

async function openImportModal() {
    const modal = document.getElementById('importLeadsModal');
    modal.style.display = 'flex';

    // Fetch salespeople (users) for the dropdown
    try {
        const response = await fetch('/api/users/employees?role_id=1');
        if (!response.ok) throw new Error('Ошибка загрузки продажников');
        const salespeople = await response.json();

        const select = document.getElementById('salespersonSelect');
        select.innerHTML = '<option value="">-- Выберите продажника --</option>';
        salespeople.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = user.first_name + " " + user.last_name || `ID: ${user.id}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Ошибка при загрузке продажников:', error);
        showNotification('Не удалось загрузить список продажников.', 'error');
    }
}

// Close the import leads modal
function closeImportModal() {
    const modal = document.getElementById('importLeadsModal');
    modal.style.display = 'none';
}

async function importLeads() {
    const form = document.getElementById('importLeadsForm');
    const formData = new FormData(form);

    const salespersonId = formData.get('salesperson');
    const googleSheetUrl = formData.get('google_sheet_url') || '';
    const file = formData.get('lead_file');

    const hasFile = file && file.size > 0 && file.name !== '';
    const hasUrl = googleSheetUrl.trim() !== '';
    if (!salespersonId) {
        showNotification('Пожалуйста, выберите продажника.', 'error');
        return;
    }

    if (!hasFile && !hasUrl) {
        showNotification('Пожалуйста, выберите файл или укажите URL Google Sheets.', 'error');
        return;
    }

    if (hasFile && hasUrl) {
        showNotification('Выберите либо файл, либо URL Google Sheets, но не оба.', 'error');
        return;
    }

    try {
        const response = await fetch('/api/leads/import', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка при импорте лидов');
        }

        showNotification('Лиды успешно импортированы!');
        closeImportModal();
        loadLeads(); // Refresh the lead list
    } catch (error) {
        console.error('Ошибка при импорте лидов:', error);
        showNotification(error.message, 'error');
    }
}




// Update statistics every 5 minutes
document.addEventListener('DOMContentLoaded', () => {
    fetchEmployees();
    loadLeads();
    fetchDailyStatistics();
    setInterval(fetchDailyStatistics, 300000);
});
// Привязка кнопок
