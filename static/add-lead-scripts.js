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
