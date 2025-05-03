"use strict";


let flatpickrInstance;

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


function generateRandomPassword() {
    const passwordLength = 10;
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()';
    let randomPassword = '';

    for (let i = 0; i < passwordLength; i++) {
        const randomIndex = Math.floor(Math.random() * characters.length);
        randomPassword += characters[randomIndex];
    }

    document.getElementById('passwordInput').value = randomPassword;
}

// Показ/скрытие пароля
function togglePasswordVisibility() {
    const passwordInput = document.getElementById('passwordInput');
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
    } else {
        passwordInput.type = 'password';
    }
}

function convertDateFormat(dateStr) {
    const [day, month, year] = dateStr.split('.');
    return `${year}-${month}-${day}`;
}

document.getElementById('employeeForm').addEventListener('submit',  async function (e) {
     // Отключаем стандартное поведение формы
e.preventDefault();
    // Очистим предыдущие ошибки
    document.querySelectorAll('.error').forEach(el => el.remove());
    document.querySelectorAll('.info-input, .input-field').forEach(el => el.classList.remove('input-error'));

    let isValid = true;

    // Проверяем каждое поле
    const fieldsToValidate = [
        { id: 'fullName', message: 'Пожалуйста, укажите имя и фамилию.' },
        { id: 'birthDate', message: 'Введите корректную дату рождения.' },
        { id: 'login', message: 'Введите логин.' },
        { id: 'phone', message: 'Введите телефон.' },
        { id: 'email', message: 'Введите корректный адрес почты.' },
        { id: 'passwordInput', message: 'Введите временный пароль.' }
    ];

    fieldsToValidate.forEach(field => {
        const input = document.getElementById(field.id);
        if (!input.value.trim()) {
            showError(input, field.message);
            isValid = false;
        }
    });

    const selectedRole = document.getElementById('selectedRole').textContent;
    if (selectedRole === 'Выберите должность') {
        showRoleError();
        isValid = false;
    }
    const birthDate = convertDateFormat(document.getElementById('birthDate').value);

    const [first_name, ...last_nameParts] = document.getElementById('fullName').value.trim().split(' ');
    const userData = {
        first_name: first_name || '',
        last_name: last_nameParts.join(' ') || '',
        birth_date:birthDate,
        login: document.getElementById('login').value,
        phone: document.getElementById('phone').value,
        email: document.getElementById('email').value,
        hashed_password: document.getElementById('passwordInput').value,
        role_id: selectedRoleId,  // Получаем ID выбранной роли
        work_days: [],  // Если нужно, добавьте данные рабочих дней
        company: 'RealEstate',  // Пример компании
    };

    // Отправка данных на сервер
    try {
        const response = await fetch('/api/users/add_user', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(userData)
        });

        if (!response.ok) {
            // Parse error details from API response
            let errorMessage = 'Неизвестная ошибка';
            try {
                const errorData = await response.json();
                errorMessage = errorData.details || errorData.detail || errorData.message || JSON.stringify(errorData);
            } catch (_) {
                // ignore JSON parse errors
            }
            throw new Error(errorMessage);
        }

        const result = await response.json();
        // Display success message at top of form
        const form = document.getElementById('employeeForm');
        // Remove any previous form-level messages
        form.querySelectorAll('.form-error, .form-success').forEach(el => el.remove());
        const successMessage = document.createElement('div');
        successMessage.classList.add('form-success');
        successMessage.textContent = 'Пользователь успешно добавлен: ' + result.first_name + ' ' + result.last_name;
        form.prepend(successMessage);

        // Redirect to admin dashboard after a short delay
        setTimeout(() => {
            window.location.href = '/dashboard/admin';
        }, 1500);
    } catch (error) {
        console.error('Ошибка:', error);
        // Display error message at top of form
        const form = document.getElementById('employeeForm');
        // Remove any previous form-level errors
        form.querySelectorAll('.form-error').forEach(el => el.remove());
        const formError = document.createElement('div');
        formError.classList.add('form-error');
        formError.textContent = error.message;
        form.prepend(formError);
    }
});

function showError(input, message) {
    const error = document.createElement('div');
    error.classList.add('error');
    error.textContent = message;
    input.classList.add('input-error');
    input.parentNode.appendChild(error);
}

function showRoleError() {
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

function openFlatpickr() {
    if (!flatpickrInstance) {
        // Инициализация Flatpickr при первом открытии
        flatpickrInstance = flatpickr("#birthDate", {
            dateFormat: "d.m.Y", // Формат даты ДД.ММ.ГГГГ
            allowInput: false,   // Отключаем ввод текста вручную
            defaultDate: null,   // Без начальной даты
            onReady: function() {
                document.getElementById('birthDate').focus(); // Открываем календарь при готовности
            }
        });
    }
    flatpickrInstance.open();  // Открываем календарь вручную при нажатии на иконку
}