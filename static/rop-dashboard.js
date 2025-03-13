// static/rop-dashboard.js
document.addEventListener("DOMContentLoaded", function () {
    // Пример: если у вас есть фильтрация дат, можете взять их из UI.
    // Здесь для примера жёстко укажем период:
    const startDate = "2025-01-01";
    const endDate = "2025-12-31";
  
    // Формируем URL для запроса
    const url = `/api/rop/dashboard?start_date=${startDate}&end_date=${endDate}`;
  
    // Делаем запрос
    fetch(url)
      .then(response => {
        if (!response.ok) {
          throw new Error(`Ошибка запроса: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        console.log("Данные с сервера:", data);
  
        // 1. Суммарная прибыль
        const totalProfitElem = document.getElementById("total-profit-count");
        if (totalProfitElem) {
          totalProfitElem.textContent = data.total_profit + " сум";
        }
  
        // 2. Общие расходы
        const totalExpensesElem = document.getElementById("total-expenses-count");
        if (totalExpensesElem) {
          totalExpensesElem.textContent = data.total_expenses + " сум";
        }
  
        // 3. Чистая прибыль
        const netProfitElem = document.getElementById("net-profit-count");
        if (netProfitElem) {
          netProfitElem.textContent = data.net_profit + " сум";
        }
  
        // 4. Закрытые сделки
        const closedDealsContainer = document.getElementById("closed-deals-container");
        if (closedDealsContainer) {
          closedDealsContainer.innerHTML = ""; // очистим на всякий случай
          data.closed_deals.forEach(lead => {
            const card = document.createElement("div");
            card.classList.add("lead-card");
            card.innerHTML = `
              <div class="lead-info">
                <h4>${lead.full_name}</h4>
                <p>Телефон: ${lead.phone}</p>
                <p>Регион: ${lead.region}</p>
                <p>Статус: ${lead.status}</p>
              </div>
            `;
            closedDealsContainer.appendChild(card);
          });
        }
  
        // 5. Бытовые затраты
        const householdContainer = document.getElementById("household-expenses-container");
householdContainer.innerHTML = "";
data.household_expenses.forEach(exp => {
  const expenseCard = createExpenseCard(exp);
  householdContainer.appendChild(expenseCard);
});

// Заполняем карточки расходов на зарплаты
const salaryContainer = document.getElementById("salary-expenses-container");
salaryContainer.innerHTML = "";
data.salary_expenses.forEach(exp => {
  const expenseCard = createExpenseCard(exp);
  salaryContainer.appendChild(expenseCard);
});
      })
      .catch(error => {
        console.error("Ошибка при получении данных:", error);
      });
  });
  /**
 * Функция для создания карточки расхода с возможностью разворачивания деталей.
 * @param {Object} exp - Объект расхода, полученный из API.
 * @returns {HTMLElement} - DOM-элемент карточки расхода.
 */
function createExpenseCard(exp) {
    // Корневой элемент карточки
    const card = document.createElement("div");
    card.classList.add("expense-card");
  
    // Основной блок с информацией о расходе
    const infoDiv = document.createElement("div");
    infoDiv.classList.add("expense-info");
    infoDiv.innerHTML = `
      <h4>${exp.title}</h4>
      <p>Сумма: ${exp.amount} сум</p>
      <p>Дата оплаты: ${new Date(exp.payment_date).toLocaleDateString("ru-RU")}</p>
      <p>Описание: ${exp.description || "—"}</p>
      <p>Статус: ${exp.status}</p>
      <p>Категория: ${exp.category}</p>
    `;
  
    // Контейнер для кнопки‑стрелки (иконки, по клику на которую разворачиваются детали)
    const toggleBtn = document.createElement("div");
    toggleBtn.classList.add("toggle-details");
    toggleBtn.innerHTML = `
      <svg class="arrow-icon" width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M4 6l4 4 4-4" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    `;
    // При клике переключаем отображение деталей
    toggleBtn.addEventListener("click", () => {
      const details = card.querySelector(".expense-details");
      if (details.style.display === "none" || details.style.display === "") {
        details.style.display = "block";
        toggleBtn.querySelector(".arrow-icon").style.transform = "rotate(180deg)";
      } else {
        details.style.display = "none";
        toggleBtn.querySelector(".arrow-icon").style.transform = "rotate(0deg)";
      }
    });
  
    // Вставляем кнопку-стрелку в основной блок (можно расположить справа)
    infoDiv.appendChild(toggleBtn);
  
    // Блок с дополнительной информацией (по умолчанию скрыт)
    const detailsDiv = document.createElement("div");
    detailsDiv.classList.add("expense-details");
    detailsDiv.style.display = "none";
    // Допустим, дополнительная информация может содержать подтверждающие заметки или файлы
    detailsDiv.innerHTML = `
      <p><strong>Дополнительная информация:</strong></p>
      <p>${exp.confirmation_note ? exp.confirmation_note : "Нет дополнительной информации"}</p>
    `;
  
    // Собираем карточку: основная информация + блок деталей
    card.appendChild(infoDiv);
    card.appendChild(detailsDiv);
  
    return card;
  }