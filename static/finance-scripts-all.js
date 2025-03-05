"use strict";

class LeadManager {
  constructor() {
    this.selectedItem = null;
    this.salesStatsData = null;
    this.initializeEventListeners();
    this.loadInitialData();
  }

  initializeEventListeners() {
    document.body.addEventListener('click', (e) => {
      const item = e.target.closest('.saller-item');
      if (item) {
        e.preventDefault();
        e.stopPropagation();

        if (this.selectedItem) {
          this.selectedItem.classList.remove('selected');
        }
        item.classList.add('selected');
        this.selectedItem = item;

        const userId = item.dataset.userId;
        this.fetchAndDisplayLeads(userId);
      }
    });

    document.body.addEventListener('click', (e) => {
      const allButton = e.target.closest('.all-report-button');
      if (allButton) {
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

  async loadInitialData() {
    try {
      await this.fetchSalesStats();
      if (!this.salesStatsData || !this.salesStatsData.sales_reps) {
        console.error('Не удалось загрузить статистику продавцов. Дальнейшая загрузка прервана.');
        return;
      }
      await this.fetchEmployees();
      await this.fetchAndDisplayLeads();
    } catch (error) {
      console.error('Ошибка при загрузке начальных данных:', error);
    }
  }

  async fetchSalesStats(userId = null) {
    try {
      const url = userId
        ? `/api/users/sales/stats?user_id=${userId}`
        : '/api/users/sales/stats';
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Ошибка HTTP: ${response.status}`);
      }
      const data = await response.json();
      this.salesStatsData = data;
      console.log('Успешно загружена статистика продавцов:', this.salesStatsData);
      return this.salesStatsData;
    } catch (error) {
      console.error('Ошибка при загрузке статистики продаж:', error);
      this.salesStatsData = null;
      return null;
    }
  }

  async fetchEmployees() {
    try {
      const response = await fetch(`/api/users/employees?role_id=1`);
      if (!response.ok) {
        throw new Error(`Ошибка HTTP: ${response.status}`);
      }
      const employees = await response.json();

      const leadList = document.querySelector('.column[data-status="SALES"] .lead-list');
      leadList.innerHTML = "";

      const allButton = document.createElement("button");
      allButton.classList.add("all-report-button");
      allButton.type = "button";
      allButton.innerHTML = `Все 
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="25" viewBox="0 0 24 25" fill="none">
          <path d="M9 5.5L15 12.5L9 19.5" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`;
      leadList.appendChild(allButton);

      employees.forEach(user => {
        const userStats = this.salesStatsData?.sales_reps?.find(stat => stat.id === user.id) || {
          stats: { new_leads: 0, processed_leads: 0, mailing_leads: 0, paid_leads: 0 }
        };

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
                <span>На рассрочке</span>
                <span>${userStats.stats.mailing_leads}</span>
              </div>
              <div class="come-lead">
                <span>Оплачено</span>
                <span>${userStats.stats.paid_leads}</span>
              </div>
            </div>
          </div>
        `;

        leadList.innerHTML += employeeItem;
      });
    } catch (error) {
      console.error('Ошибка при загрузке сотрудников:', error);
    }
  }

  async fetchAndDisplayLeads(userId = null) {
    try {
      document.body.style.cursor = 'wait';

      const url = userId
        ? `/api/leads/filter?user_id=${userId}`
        : '/api/leads/filter';

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      this.updateLeadsDisplay(data);
    } catch (error) {
      console.error('Ошибка при загрузке лидов:', error);
    } finally {
      document.body.style.cursor = 'default';
    }
  }

  updateLeadsDisplay(data) {
    const installmentColumn = document.querySelector('[data-status="installment"]');
    if (installmentColumn) {
      installmentColumn.querySelector('.lead-count').textContent = `${data.mailing_leads.count}`;
      const leadList = installmentColumn.querySelector('.lead-list');
      leadList.innerHTML = data.mailing_leads.leads.map(lead => this.createLeadCard(lead)).join('');
    }

    const paidColumn = document.querySelector('[data-status="paid"]');
    if (paidColumn) {
      paidColumn.querySelector('.lead-count').textContent = `${data.paid_leads.count}`;
      const leadList = paidColumn.querySelector('.lead-list');
      leadList.innerHTML = data.paid_leads.leads.map(lead => this.createLeadCard(lead)).join('');
    }
  }

  createLeadCard(lead) {
    let mailingPayments = 0;
    if (this.salesStatsData && Array.isArray(this.salesStatsData.sales_reps)) {
      if (this.selectedItem && this.selectedItem.dataset && this.selectedItem.dataset.userId) {
        const userId = parseInt(this.selectedItem.dataset.userId);
        const rep = this.salesStatsData.sales_reps.find(r => r.id === userId);
        if (rep && Array.isArray(rep.stats.mailing_details)) {
          const leadDetail = rep.stats.mailing_details.find(d => d.lead_id === lead.id);
          mailingPayments = leadDetail ? leadDetail.mailing_payments : 0;
        }
      } else {
        for (const rep of this.salesStatsData.sales_reps) {
          if (Array.isArray(rep.stats.mailing_details)) {
            const leadDetail = rep.stats.mailing_details.find(d => d.lead_id === lead.id);
            if (leadDetail) {
              mailingPayments = leadDetail.mailing_payments;
              break;
            }
          }
        }
      }
    } else {
      console.warn('Данные статистики продавцов недоступны или некорректны:', this.salesStatsData);
    }

    const isOverdue = lead.status === 'просрочено';
    const cardClass = isOverdue ? 'card overdue' : 'card';
    const nameClass = isOverdue ? 'name overdue-name' : 'name';

    return `
      <div class="${cardClass}">
        <div class="card-header">
          <div class="${nameClass}">${lead.full_name}</div>
          <div class="date">${lead.date}</div>
        </div>
        <hr class="divider">
        <div class="contact-info">
          <span class="messenger elements-info ${lead.contact_source}">${lead.contact_source}</span>
          <span class="location elements-info">${lead.region}</span>
          <span class="phone elements-info">${lead.phone}</span>
        </div>
        <hr class="divider">
        <div class="payment-info">Следующая оплата: ${lead.next_due_date}</div>
        <div class="payment-info">Сумма сделки: ${lead.total_price.toLocaleString()} ${lead.currency}</div>
        <hr class="divider">
        <div class="whose-lead">Ответственный менеджер: ${lead.user}</div>
        <hr class="divider">
        <div class="status">
          <div class="status-indicator">
            <span class="status-dot" style="background-color: ${this.getStatusColor(lead.status)}"></span>
            <span>${lead.status}</span>
          </div>
          <a href="/dashboard/finance/lead/${lead.id}" class="open-card">Открыть карточку</a>
        </div>
      </div>
    `;
  }

  getStatusColor(status) {
    const colors = {
      'на рассылке': '#FFA500',
      'оплачено': '#00FF55',
      'просрочено': '#FF0000'
    };
    return colors[status] || '#CCCCCC';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.leadManager = new LeadManager();
});


