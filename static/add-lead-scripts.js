// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Показываем секцию рассрочки по умолчанию (так как "Рассрочка" активна)
    const installmentSection = document.getElementById('installment-period-section');
    if (installmentSection) {
        installmentSection.style.display = 'block';
    }
});

// Переключение валюты
document.querySelectorAll('.currency-button').forEach(button => {
    button.addEventListener('click', () => {
        // Убираем активный класс со всех кнопок
        document.querySelectorAll('.currency-button').forEach(btn => btn.classList.remove('active'));
        // Добавляем активный класс к выбранной кнопке
        button.classList.add('active');
        console.log(`Выбрана валюта: ${button.dataset.currency}`);
    });
});

// Переключение на рассрочку
document.querySelectorAll('.installment-button').forEach(button => {
    button.addEventListener('click', () => {
        // Убираем активный класс со всех кнопок
        document.querySelectorAll('.installment-button').forEach(btn => btn.classList.remove('active'));
        // Добавляем активный класс к выбранной кнопке
        button.classList.add('active');
        
        // Показываем или скрываем секцию срока рассрочки
        const installmentSection = document.getElementById('installment-period-section');
        const paymentType = button.textContent.trim();
        
        if (paymentType === 'Единовременно') {
            installmentSection.style.display = 'none';
        } else {
            installmentSection.style.display = 'block';
        }
        
        console.log(`Выбран тип оплаты: ${paymentType}`);
    });
});

// Форматирование суммы при вводе
function formatAmount(input) {
    let value = input.value.replace(/,/g, '').replace(/[^\d]/g, '');
    input.value = new Intl.NumberFormat('en-US').format(value);
}

let selectedPeriod = 0;

const periodButtons = document.querySelectorAll('.period-button');
const manualInput = document.getElementById('manualMonthsInput');

// Обработчик клика по кнопкам периода
periodButtons.forEach(button => {
    button.addEventListener('click', () => {
        // Сбрасываем выделение всех кнопок
        periodButtons.forEach(btn => btn.classList.remove('active'));
        // Добавляем активный класс к нажатой кнопке
        button.classList.add('active');
        // Устанавливаем значение в поле ввода и сохраняем
        const selectedValue = button.getAttribute('data-months');
        manualInput.value = selectedValue;
        selectedPeriod = parseInt(selectedValue); // Сохраняем значение

        console.log('Выбрано значение:', selectedPeriod); // Для проверки
    });
});

// Обработчик ручного ввода
manualInput.addEventListener('input', () => {
    // Убираем выделение кнопок, если пользователь вводит вручную
    if (manualInput.value.trim() !== '') {
        periodButtons.forEach(btn => btn.classList.remove('active'));
        selectedPeriod = parseInt(manualInput.value.trim()) || 0; // Сохраняем ручное значение

        console.log('Введено вручную:', selectedPeriod); // Для проверки
    }
});



function toggleDropdown() {
    const dropdownList = document.getElementById('dropdownList');
    dropdownList.classList.toggle('visible');
}
let selectedRoleId = null;

function selectRole(roleName, roleId) {
    document.getElementById('selectedRole').textContent = roleName;
    selectedRoleId = roleId; 
    // Закрываем выпадающий список
    document.getElementById('dropdownList').classList.remove('visible');
}

// Закрытие списка при клике вне его
document.addEventListener('click', function (event) {
    const dropdown = document.getElementById('dropdownContainer');
    const dropdownList = document.getElementById('dropdownList');

    // Проверяем, произошёл ли клик вне выпадающего списка
    if (!dropdown.contains(event.target)) {
        dropdownList.classList.remove('visible');
    }
});

async function getCurrentUser() {
    try {
        const response = await fetch('/user/me');
        const currentUser = await response.json();
        return currentUser;
    } catch (error) {
        console.error('Ошибка при получении текущего пользователя:', error);
        return null;
    }
    
}


document.getElementById("employeeForm").addEventListener("submit", async function (event) {
    event.preventDefault(); // Предотвращаем перезагрузку страницы
    currentUser = await getCurrentUser();

    document.querySelectorAll('.error').forEach(el => el.remove());
    document.querySelectorAll('.info-input, .input-field').forEach(el => el.classList.remove('input-error'));

    let isValid = true;

    // Проверяем каждое поле
    const fieldsToValidate = [
        { id: 'fullName', message: 'Пожалуйста, укажите имя и фамилию.' },
        { id: 'phone', message: 'Введите телефон.' },

    ];

    fieldsToValidate.forEach(field => {
        const input = document.getElementById(field.id);
        if (!input.value.trim()) {
            showError(input, field.message);
            isValid = false;
        }
    });

    // Validate region selection
    const selectedRegionText = document.getElementById('selectedRegion').textContent;
    if (selectedRegionText === 'Выберите регион') {
        showError(document.getElementById('regionContainer'), 'Выберите регион.');
        isValid = false;
    }

    const selectedRole = document.getElementById('selectedRole').textContent;
    if (selectedRole === 'Выберите источник') {
        showRoleError();
        isValid = false;
    }
    let total_price = parseFloat(document.getElementById("amountInput").value.replace(/,/g, "")) || 0;
    let installment_period = parseInt(document.getElementById("manualMonthsInput").value) || 0;
let installment_markup = 10;
monthly_payment = total_price * (1 + installment_markup / 100) / installment_period;

    // Получаем данные из формы
    const leadData = {
        full_name: document.getElementById("fullName").value,
        phone: document.getElementById("phone").value,
        region: document.getElementById('selectedRegion').textContent,
        contact_source: document.getElementById("selectedRole").textContent.trim(), // Источник лида
        status: "COLD",  // Выбор статуса
        state: "NEW",    // Выбор состояния
        square_meters: parseFloat(document.querySelector(".option-item input[placeholder='180']").value) || null,
        rooms: parseInt(document.querySelector(".option-item input[placeholder='5']").value) || null,
        floor: parseInt(document.querySelector(".option-item input[placeholder='0']").value) || null,
        number_apartments: parseInt(document.querySelector(".option-item input[placeholder='98']").value) || null, // Номер квартиры
        complex_name: window.selectedComplex || null, // Название жилого комплекса
        block: window.selectedBlock || null, // Блок
        total_price: total_price, // Убираем запятые
        currency: document.querySelector(".currency-button.active").getAttribute("data-currency"),
        payment_type: document.querySelector(".installment-button.active").textContent.trim(),
        monthly_payment: monthly_payment, // Можно добавить расчет
        installment_period: installment_period,
        installment_markup: installment_markup, // Можно добавить расчет
        down_payment: window.selectedDownPayment || null, // Первоначальный взнос
        down_payment_percent: window.selectedDownPaymentPercent || null, // Процент первоначального взноса
        notes: "",
        next_contact_date: null,
        user_id: currentUser.id // Получаем ID текущего пользователя
    };

    try {
        // 1. Создаём лид
        const leadResponse = await fetch("/api/leads/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(leadData),
        });

        const leadResult = await leadResponse.json();
        if (!leadResponse.ok) {
            console.error("Ошибка при добавлении лида:", leadResult);
            alert("Ошибка: " + (leadResult.detail || "Не удалось добавить лид"));
            return;
        }

        const leadId = leadResult.id; // Получаем ID созданного лида

        // 2. Если это рассрочка или гибридная, создаём план платежей и первоначальный платеж
        if ((leadData.payment_type === "Рассрочка" || leadData.payment_type === "Гибридная") && leadData.installment_period) {
            // Создаём план рассрочки (если API поддерживает InstallmentPlan)
            const installmentPlanData = {
                lead_id: leadId,
                total_amount: leadData.total_price,
                number_of_payments: leadData.installment_period,
                start_date: new Date().toISOString()
            };

            const installmentPlanResponse = await fetch("/api/finance/installments/plan", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(installmentPlanData),
            });

            const installmentPlanResult = await installmentPlanResponse.json();
            if (!installmentPlanResponse.ok) {
                console.error("Ошибка при создании плана рассрочки:", installmentPlanResult);
                alert("Ошибка: Не удалось создать план рассрочки");
                return;
            }

            // Создаём первоначальный платеж (initial payment)
            const initialPaymentData = {
                lead_id: leadId,
                amount: leadData.monthly_payment,
                due_date: new Date().toISOString(),
                payment_type: "installment"
            };

            const initialPaymentResponse = await fetch("/api/finance/payments/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(initialPaymentData),
            });

            const initialPaymentResult = await initialPaymentResponse.json();
            if (!initialPaymentResponse.ok) {
                console.error("Ошибка при создании первоначального платежа:", initialPaymentResult);
                alert("Ошибка: Не удалось создать первоначальный платеж");
                return;
            }
        }
        // 3. Если это единовременный платеж, создаём полный платеж
        else if (leadData.payment_type === "Единовременно") {
            const fullPaymentData = {
                lead_id: leadId,
                amount: leadData.total_price,
                due_date: new Date().toISOString(),
                payment_type: "full"
            };

            const fullPaymentResponse = await fetch("/api/finance/payments/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(fullPaymentData),
            });

            const fullPaymentResult = await fullPaymentResponse.json();
            if (!fullPaymentResponse.ok) {
                console.error("Ошибка при создании полного платежа:", fullPaymentResult);
                alert("Ошибка: Не удалось создать полный платеж");
                return;
            }
        }

        alert("Лид успешно добавлен!");
        // Можно добавить сброс формы или перенаправление
        window.location.href = '/dashboard/sales';

    } catch (error) {
        console.error("Ошибка сети:", error);
        alert("Ошибка сети! Проверьте подключение к серверу.");
    }
});


function showError(input, message) {
    const error = document.createElement('div');
    error.classList.add('error');
    input.classList.add('input-error');
    input.parentNode.appendChild(error);
}

function showRoleError(message) {
    const dropdownContainer = document.getElementById('dropdownContainer');

    // Убираем старые ошибки, если они есть
    document.querySelectorAll('.error').forEach(el => el.remove());

    

    // Прокрутка к элементу
    dropdownContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });

    // Подсветка элемента
    dropdownContainer.classList.add('highlight-error');

    // Убираем подсветку через 2 секунды
    setTimeout(() => {
        dropdownContainer.classList.remove('highlight-error');
    }, 2000);
}
