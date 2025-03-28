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