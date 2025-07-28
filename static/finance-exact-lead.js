"use strict";

class LeadDetailManager {
  constructor(leadId) {
    this.leadId = leadId;
    this.leadData = null;
    this.initialize();
  }

  async initialize() {
    await this.fetchLeadDetails();
    if (this.leadData) {
      this.updateActionButtons();
      this.addModal();
      this.addEventListeners();
    }
  }

  async fetchLeadDetails() {
    try {
      const response = await fetch(`/api/finance/leads/${this.leadId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      this.leadData = await response.json();
      console.log('Данные лида загружены:', this.leadData);
    } catch (error) {
      console.error('Ошибка при загрузке данных лида:', error);
    }
  }

  updateActionButtons() {
    if (!this.leadData) {
      console.error('Данные лида отсутствуют');
      return;
    }

    const actionsContainer = document.querySelector('.actions');
    if (!actionsContainer) {
      console.error('Контейнер .actions не найден');
      return;
    }

    // Обновляем кнопку "Погашенная сумма"
    const paidAmountButton = actionsContainer.querySelector('.action-button-finance:nth-child(2)');
    if (paidAmountButton) {
      paidAmountButton.querySelector('p').textContent = `Погашенная сумма (${this.leadData.paid_months} месяцев)`;
      paidAmountButton.querySelector('.monthly-price').textContent = `${this.leadData.paid_amount.toLocaleString()} ${this.leadData.currency}`;

    }

    // Обновляем кнопку "Дедлайн для погашения месяца"
    const dueDateButton = actionsContainer.querySelector('.action-button-finance:nth-child(3)');
    if (dueDateButton) {
      const dueDateText = this.leadData.next_due_date || 'Нет предстоящих платежей';
      const overdueText = this.leadData.is_next_due_date_overdue ? ' (просрочена)' : '';
      const monthlyPrice = dueDateButton.querySelector('.monthly-price');
      monthlyPrice.textContent = `${dueDateText}${overdueText}`;
      if (this.leadData.is_next_due_date_overdue) {
        monthlyPrice.classList.add('overdue-due-date');
      }
    }

    // Добавляем обработчик для кнопки "История оплат клиентом"
    const paymentHistoryButton = actionsContainer.querySelector('.action-button-finance:nth-child(1)');
    if (paymentHistoryButton) {
      paymentHistoryButton.addEventListener('click', () => this.showPaymentHistory());
    }
  }

  addModal() {
    // Подсчитываем количество оставшихся месяцев
    const remainingMonths = this.leadData.installment_period - this.leadData.paid_months;

    const modalHtml = `
      <div class="modal" id="paid-amount-modal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Погашенная сумма</h3>
            <button class="modal-close" onclick="window.leadDetailManager.closeModal('paid-amount-modal')">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12"></path>
              </svg>
            </button>
          </div>
          <div class="modal-body">
            <div class="payment-summary">
              <span>Погашено</span>
              <span class="amount-paid">${this.leadData.paid_amount.toLocaleString()} ${this.leadData.currency}</span>
            </div>
            <div class="payment-remaining">
              <span>Осталось выплат</span>
              <span class="remaining-count">${remainingMonths}</span>
            </div>
            ${
              this.leadData.payment_history && this.leadData.payment_history.length > 0
                ? this.leadData.payment_history.map(payment => `
                    <div class="payment-history-item">
                      <div class="payment-date">${payment.due_date}</div>
                      <div class="payment-details">
                        <span class="payment-status">
                          ${
                            payment.status === 'paid'
                              ? 'Оплачено'
                              : payment.status === 'pending'
                              ? 'Ожидаем оплаты' + (payment.is_overdue ? ' (просрочено)' : '')
                              : 'Просрочено'
                          }
                          ${
                            payment.status === 'pending'
                              ? '<svg class="pending-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 0 0-10 10v2h2v-2a8 8 0 0 1 8-8 8 8 0 0 1 8 8v2h2v-2a10 10 0 0 0-10-10zM12 6v6l4 2"/></svg>'
                              : ''
                          }
                        </span>
                        <span class="payment-amount">${payment.amount.toLocaleString()} ${this.leadData.currency}</span>
                      </div>
                    </div>
                  `).join('')
                : '<div>История платежей отсутствует</div>'
            }
          </div>
        </div>
      </div>
      <div class="modal" id="payment-history-modal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h3>История оплат</h3>
            <button class="modal-close" onclick="window.leadDetailManager.closeModal('payment-history-modal')">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
  <path d="M17 7.00004L7.00004 17M7 7L17 17" stroke="black" stroke-width="1.5" stroke-linecap="round"/>
</svg>
            </button>
          </div>
          <div class="modal-body">
            <div class="payment-summary">
              <span>Погашено</span>
              <span class="amount-paid">${this.leadData.paid_amount.toLocaleString()} ${this.leadData.currency}</span>
            </div>
            <div class="payment-remaining">
              <span>Осталось выплат</span>
              <span class="remaining-count">${remainingMonths}</span>
            </div>
            ${
              this.leadData.payment_history && this.leadData.payment_history.length > 0
                ? this.leadData.payment_history.map(payment => `
                    <div class="payment-history-item">
                      <div class="payment-date">${payment.due_date}</div>
                      <div class="payment-details">
                        <span class="payment-status">
                          ${
                            payment.status === 'paid'
                              ? 'Оплачено'
                              : payment.status === 'pending'
                              ? 'Ожидаем оплаты' + (payment.is_overdue ? ' (просрочено)' : '')
                              : 'Просрочено'
                          }
                          ${
                            payment.status === 'pending'
                              ? '<svg class="pending-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 0 0-10 10v2h2v-2a8 8 0 0 1 8-8 8 8 0 0 1 8 8v2h2v-2a10 10 0 0 0-10-10zM12 6v6l4 2"/></svg>'
                              : ''
                          }
                        </span>
                        <span class="payment-amount">${payment.amount.toLocaleString()} ${this.leadData.currency}</span>
                      </div>
                    </div>
                  `).join('')
                : '<div>История платежей отсутствует</div>'
            }
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
  }

  addEventListeners() {
    // Здесь можно добавить дополнительные обработчики событий, если нужно
  }



  showPaymentHistory() {
    const modal = document.getElementById('payment-history-modal');
    if (modal) {
      modal.style.display = 'flex';
    }
  }

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.style.display = 'none';
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  // Извлекаем lead_id из пути URL
  const pathParts = window.location.pathname.split('/');
  const leadId = pathParts[pathParts.length - 1];
  const leadIdNumber = parseInt(leadId, 10);
  if (isNaN(leadIdNumber)) {
    console.error('Некорректный lead_id в URL:', leadId);
    return;
  }

  window.leadDetailManager = new LeadDetailManager(leadIdNumber);
});