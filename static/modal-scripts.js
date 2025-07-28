let selectedRole = '';  // Для хранения выбранной должности


function reassign() {
    // Открываем модальное окно
    const modal = document.getElementById('reassignModal');
    modal.classList.add('visible');
}

function resetPassword() {
    // Открываем модальное окно
    const modal = document.getElementById('resetPasswordModal');
    modal.classList.add('visible');
}

function copyToClipboard() {
    const password = document.getElementById('temporaryPassword').textContent;
    navigator.clipboard.writeText(password).then(() => {
        showNotification('Пароль успешно скопирован!');
    }).catch(err => {
        console.error('Не удалось скопировать пароль: ', err);
    });
}

function showNotification(message) {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.classList.add('show');

    // Скрываем уведомление через 3 секунды
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

function confirmReassign() {
    closeModal();  // Закрываем первое модальное окно
    openSelectRoleModal();  // Открываем второе модальное окно
}

function openSelectRoleModal() {
    const modal = document.getElementById('selectRoleModal');
    modal.classList.add('visible');
}

function selectRole(role) {
    selectedRole = role;
    

    // Удаляем класс "active" у всех кнопок
    document.querySelectorAll('.role-button').forEach(button => {
        button.classList.remove('active');

        // Добавляем класс "active" кнопке с соответствующим текстом
        if (button.textContent.trim() === role) {
            button.classList.add('active');
            selectedRoleId = button.getAttribute('data-role-id');
        }
    });

    // Активируем кнопку "Далее"
    document.getElementById('confirmRoleButton').disabled = false;
}

function deleteUser() {
    // Открываем модальное окно
    const modal = document.getElementById('deleteUserModal');
    modal.classList.add('visible');
}

function openSuccessModal(title = '', description = '') {
    // Заменяем текст в модальном окне
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalDescription').textContent = description;

    closeModal();  // Закрываем предыдущие модальные окна
    document.getElementById('successModal').classList.add('visible');
}

function openSuccessPasswordModal() {


    closeModal();  // Закрываем предыдущие модальные окна
    document.getElementById('successModalPassword').classList.add('visible');
}



function closeModal() {
    document.querySelectorAll('.modal').forEach(modal => modal.classList.remove('visible'));
}

function closeAllModal() {
    document.querySelectorAll('.modal').forEach(modal => modal.classList.remove('visible'));
    window.location.reload();
}

function copyToClipboard() {
    const password = document.getElementById('temporaryPassword').textContent;
    console.log(password)
    navigator.clipboard.writeText(password).then(() => {
        showNotification('Пароль успешно скопирован!');
    }).catch(err => {
        console.error('Не удалось скопировать пароль: ', err);
    });
}

function showNotification(message) {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.classList.add('show');

    // Скрываем уведомление через 3 секунды
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}