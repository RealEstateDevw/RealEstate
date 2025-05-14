"use strict";


window.onload = () => {
filterEmployees();
};


async function fetchSalesStats(userId = null) {
    try {
        const url = userId ? `/api/users/sales/stats?user_id=${userId}` : `/api/users/sales/stats`;
        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error('Ошибка при загрузке статистики продаж:', error);
        return null;
    }
}

async function filterEmployees() {
    try {
        // Загружаем список сотрудников
        const response = await fetch(`/api/users/employees?role_id=1`);
        const employees = await response.json();

        // Загружаем общую статистику
        const salesStats = await fetchSalesStats();

        // Очищаем текущий список сотрудников (чтобы не дублировалось)
        const leadList = document.querySelector('.lead-list');
        leadList.innerHTML = "";

        // Создаем кнопку "Все"
        const allButton = document.createElement("button");
        allButton.classList.add("all-report-button");
        allButton.type = "button";
        allButton.innerHTML = `Все 
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="25" viewBox="0 0 24 25" fill="none">
                <path d="M9 5.5L15 12.5L9 19.5" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>`;
        allButton.addEventListener("click", async () => {
            await filterEmployees(); // Перезагружаем весь список
        });

        leadList.appendChild(allButton);

        // Генерируем новый список сотрудников
        employees.forEach(user => {
            const userStats = salesStats?.sales_reps?.find(stat => stat.id === user.id) || { stats: { new_leads: 0, processed_leads: 0 } };
            console.log(userStats);
            console.log( user.work_status);
            const workStatus = user.work_status === 'Рабочий' && user.checkin_time
                ? `<rect y="0.5" width="16" height="16" rx="8" fill="#00FF55"/>`
                : user.work_status === 'Выходной'
                ? `<rect y="0.5" width="16" height="16" rx="8" fill="#A0A0A0"/>`
                : `<rect y="0.5" width="16" height="16" rx="8" fill="#FF0000"/>`;

            const statusText = user.work_status === 'Рабочий' && user.checkin_time
                ? 'Был на работе'
                : user.work_status === 'Выходной'
                ? 'Выходной'
                : 'Отсутствовал';

            const employeeItem = `
                <div class="saller-item" data-user-id="${user.id}">
                    <div class="saller-info">
                        <div class="saller-name">${user.last_name} ${user.first_name}</div>
                        <div class="saller-position">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="17" viewBox="0 0 16 17" fill="none">
                                ${workStatus}
                            </svg>
                            ${statusText}
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="25" viewBox="0 0 24 25" fill="none">
                                <path d="M9 5.5L15 12.5L9 19.5" stroke="black" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </div>
                    </div>
                    <div class="lead-count">
                        <div class="come-lead">
                            <span>Поступило</span>
                            <span>${userStats.stats.new_leads}</span>
                        </div>
                        <div class="come-lead">
                            <span>Отработано</span>
                            <span>${userStats.stats.processed_leads}</span>
                        </div>
                    </div>
                </div>
            `;

            leadList.innerHTML += employeeItem;
        });

    } catch (error) {
        console.error('Ошибка при фильтрации сотрудников:', error);
    }
}


class LeadFilter {
    constructor() {
        console.log('LeadFilter initialized');
        this.selectedItem = null;
        this.initializeEventListeners();
        this.fetchAndDisplayLeads();
    }

    initializeEventListeners() {
        console.log('Initializing event listeners');
    
        // Делегирование событий для .saller-item (работает и для новых элементов)
        document.body.addEventListener('click', (e) => {
            const item = e.target.closest('.saller-item');
            if (item) {
                console.log('Seller item clicked:', item);
                e.preventDefault();
                e.stopPropagation();
                
                if (this.selectedItem) {
                    this.selectedItem.classList.remove('selected');
                }
                item.classList.add('selected');
                this.selectedItem = item;
    
                const userId = item.dataset.userId;
                console.log('User ID:', userId);
                this.fetchAndDisplayLeads(userId);
            }
        });
    
        // Кнопка "Все"
        document.body.addEventListener('click', (e) => {
            const allButton = e.target.closest('.all-report-button');
            if (allButton) {
                console.log('All button clicked');
                e.preventDefault();
                e.stopPropagation();

                if (this.selectedItem) {
                    this.selectedItem.classList.remove('selected');
                }
                allButton.classList.add('selected');
                this.selectedItem = allButton;

                this.fetchAndDisplayLeads();
            }
        });
    }

    async fetchAndDisplayLeads(userId = null) {
        console.log('Fetching leads for user:', userId);
        
        try {
            document.body.style.cursor = 'wait';
            
            const url = userId 
                ? `/api/leads/filter?user_id=${userId}`
                : '/api/leads/filter';
            
            console.log('Fetching from URL:', url);
            
            const response = await fetch(url);
            console.log('Response received:', response);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Data received:', data);
            
            this.updateLeadsDisplay(data);
            this.updateSellerStats(data);
        } catch (error) {
            console.error('Error fetching leads:', error);
        } finally {
            document.body.style.cursor = 'default';
        }
    }

    updateLeadsDisplay(data) {
        const incomingColumn = document.querySelector('[data-status="INCOMING"]');
        if (incomingColumn) {
            incomingColumn.querySelector('.lead-count').textContent = `${data.new_leads.count} лида`;
            const leadList = incomingColumn.querySelector('.lead-list');
            leadList.innerHTML = data.new_leads.leads.map(lead => this.createLeadCard(lead)).join('');
        }

        const processedColumn = document.querySelector('[data-status="PROCESSED"]');
        if (processedColumn) {
            processedColumn.querySelector('.lead-count').textContent = `${data.processed_leads.count} лидов`;
            const leadList = processedColumn.querySelector('.lead-list');
            leadList.innerHTML = data.processed_leads.leads.map(lead => this.createLeadCard(lead)).join('');
        }
    }

    updateSellerStats(data) {
        const sellerItems = document.querySelectorAll('.saller-item');
        sellerItems.forEach(item => {
            const userId = item.dataset.userId;
            const userStats = data.user_stats?.[userId];
            
            if (userStats) {
                const incoming = item.querySelector('.come-lead:first-child span:last-child');
                const processed = item.querySelector('.come-lead:last-child span:last-child');
                
                if (incoming) incoming.textContent = userStats.incoming_count || '0';
                if (processed) processed.textContent = userStats.processed_count || '0';
            }
        });
    }

    createLeadCard(lead) {
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
                <div class="payment-info">Предварительная сумма: ${lead.total_price.toLocaleString()}</div>
                <hr class="divider">
                <div class="whose-lead">Ответственный менеджер: ${lead.user}</div>
                <hr class="divider">
                <div class="status">
                    <div class="status-indicator">
                        <span class="status-dot" style="background-color: ${this.getStatusColor(lead.state)}"></span>
                        <span>${this.getStatusText(lead.state)}</span>
                    </div>
                    <a href="/dashboard/sales/lead/${lead.id}" class="open-card">Открыть карточку</a>
                </div>
            </div>
        `;
    }

     getStatusColor(status) {
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
     getStatusText(status) {
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
}


class SalesLeads {
    constructor() {
        this.initializeEventListeners();
        this.fetchAndDisplayStats();
    }

    initializeEventListeners() {
        // Listen for "Все" button click
        const allReportButton = document.querySelector('.all-report-button');
        if (allReportButton) {
            allReportButton.addEventListener('click', () => {
                this.fetchAndDisplayStats();
            });
        }

        // Listen for individual sales rep clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.saller-position')) {
                const sallerItem = e.target.closest('.saller-item');
                if (sallerItem) {
                    const userId = sallerItem.dataset.userId;
                    this.fetchAndDisplayStats(userId);
                }
            }
        });
    }

    async fetchAndDisplayStats(userId = null) {
        try {
            const url = userId 
                ? `/api/users/sales/stats?user_id=${userId}`
                : '/api/users/sales/stats';
            
            const response = await fetch(url);
            const data = await response.json();
            
            this.updateDisplay(data);
        } catch (error) {
            console.error('Error fetching sales stats:', error);
        }
    }

    updateDisplay(data) {
        const leadList = document.querySelector('.lead-list');
        if (!leadList) return;

        // Update total stats in "Все" button if available
        if (data.total_stats) {
            const allButton = leadList.querySelector('.all-report-button');
            if (allButton) {
                // You might want to add elements to show total stats in the button
            }
        }

        // Update or create sales rep items
        const salesContent = data.sales_reps.map(rep => this.createSalesRepItem(rep)).join('');
        
        // Insert after the "Все" button
        const allButton = leadList.querySelector('.all-report-button');
        if (allButton) {
            allButton.insertAdjacentHTML('afterend', salesContent);
        }
    }

    createSalesRepItem(rep) {
        return `
            <div class="saller-item" data-user-id="${rep.id}">
                <div class="saller-info">
                    <div class="saller-name">${rep.name}</div>
                    <div class="saller-position">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="17" viewBox="0 0 16 17" fill="none">
                            <rect y="0.5" width="16" height="16" rx="8" fill="#00FF55"/>
                        </svg>
                        ${rep.status}
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="25" viewBox="0 0 24 25" fill="none">
                            <path d="M9 5.5L15 12.5L9 19.5" stroke="black" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                </div>
                <div class="lead-count">
                    <div class="come-lead">
                        <span>Поступило</span>
                        <span>${rep.stats.new_leads}</span>
                    </div>
                    <div class="come-lead">
                        <span>Отработано</span>
                        <span>${rep.stats.processed_leads}</span>
                    </div>
                </div>
            </div>
        `;
    }
}


document.addEventListener('DOMContentLoaded', () => {
    window.leadFilter = new LeadFilter();
    // window.salesLeads = new SalesLeads();
});


