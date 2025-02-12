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
        console.log(`Выбрана рассрочка: ${button.dataset.installment}`);
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
        { id: 'regionSelect', message: 'Выберите регион.' },

    ];

    fieldsToValidate.forEach(field => {
        const input = document.getElementById(field.id);
        if (!input.value.trim()) {
            showError(input, field.message);
            isValid = false;
        }
    });

    const selectedRole = document.getElementById('selectedRole').textContent;
    if (selectedRole === 'Выберите источник') {
        showRoleError();
        isValid = false;
    }
    // Получаем данные из формы
    const leadData = {
        full_name: document.getElementById("fullName").value,
        phone: document.getElementById("phone").value,
        region: document.getElementById("regionSelect").value,
        contact_source: document.getElementById("selectedRole").textContent.trim(), // Источник лида
        status: "COLD",  // Выбор статуса
        state: "POSTPONED",    // Выбор состояния
        square_meters: parseInt(document.querySelector(".option-item input[placeholder='180']").value) || null,
        rooms: parseInt(document.querySelector(".option-item input[placeholder='5']").value) || null,
        floor: parseInt(document.querySelector(".option-item input[placeholder='0']").value) || null,
        total_price: parseFloat(document.getElementById("amountInput").value.replace(/,/g, "")) || 0, // Убираем запятые
        currency: document.querySelector(".currency-button.active").getAttribute("data-currency"),
        payment_type: document.querySelector(".installment-button.active").textContent.trim(),
        monthly_payment: null, // Можно добавить расчет
        installment_period: parseInt(document.getElementById("manualMonthsInput").value) || null,
        installment_markup: null, // Можно добавить расчет
        notes: "",
        next_contact_date: null,
        user_id: currentUser.id // Получаем ID текущего пользователя
    };

    try {
        const response = await fetch("/api/leads/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(leadData),
        });

        const result = await response.json();
        if (response.ok) {
            alert("Лид успешно добавлен!");
        } else {
            console.error("Ошибка при добавлении лида:", result);
            alert("Ошибка: " + (result.detail || "Не удалось добавить лид"));
        }
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


