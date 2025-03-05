"use strict";


const API_URL = '/api/leads';
const LEAD_ID = document.getElementById('leadId').value;


function displayResults(results) {
    const searchResults = document.getElementById('searchResults');
    searchResults.innerHTML = '';  // Очищаем список результатов

    if (results.length === 0) {
        searchResults.innerHTML = '<div class="no-results">Нет результатов</div>';
        searchResults.style.display = 'block';
    } else {
        results.forEach(result => {
            console.log(result);
            const item = document.createElement('div');
            item.classList.add('result-item');

            item.innerHTML = `
                <div class="result-name">${result.full_name}</div>
                <div class="result-role">
                   <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
<path fill-rule="evenodd" clip-rule="evenodd" d="M10 4H14C17.7712 4 19.6569 4 20.8284 5.17157C22 6.34315 22 8.22876 22 12C22 15.7712 22 17.6569 20.8284 18.8284C19.6569 20 17.7712 20 14 20H10C6.22876 20 4.34315 20 3.17157 18.8284C2 17.6569 2 15.7712 2 12C2 8.22876 2 6.34315 3.17157 5.17157C4.34315 4 6.22876 4 10 4ZM13.25 9C13.25 8.58579 13.5858 8.25 14 8.25H19C19.4142 8.25 19.75 8.58579 19.75 9C19.75 9.41421 19.4142 9.75 19 9.75H14C13.5858 9.75 13.25 9.41421 13.25 9ZM14.25 12C14.25 11.5858 14.5858 11.25 15 11.25H19C19.4142 11.25 19.75 11.5858 19.75 12C19.75 12.4142 19.4142 12.75 19 12.75H15C14.5858 12.75 14.25 12.4142 14.25 12ZM15.25 15C15.25 14.5858 15.5858 14.25 16 14.25H19C19.4142 14.25 19.75 14.5858 19.75 15C19.75 15.4142 19.4142 15.75 19 15.75H16C15.5858 15.75 15.25 15.4142 15.25 15ZM11 9C11 10.1046 10.1046 11 9 11C7.89543 11 7 10.1046 7 9C7 7.89543 7.89543 7 9 7C10.1046 7 11 7.89543 11 9ZM9 17C13 17 13 16.1046 13 15C13 13.8954 11.2091 13 9 13C6.79086 13 5 13.8954 5 15C5 16.1046 5 17 9 17Z" fill="#216BF4"/>
</svg>
                    Лид
                </div>
            `;

            // Обработчик клика на элемент
            item.addEventListener('click', () => {
                console.log(`Вы выбрали: ${result.name}`);
            });

            searchResults.appendChild(item);
        });
        searchResults.style.display = 'block';
    }
};

document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');

console.log('Элемент найден:', searchInput); 
// Обработчик ввода текста
searchInput.addEventListener('input', async () => {
    const query = searchInput.value.trim();

    if (query === '') {
        searchResults.style.display = 'none';
        return;
    }

    try {
        const response = await fetch(`${API_URL}/search?query=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error('Ошибка при получении данных');
        }

        const results = await response.json();
        displayResults(results);
    } catch (error) {
        console.error('Ошибка при поиске:', error);
        searchResults.innerHTML = '<div class="no-results">Произошла ошибка при загрузке данных</div>';
        searchResults.style.display = 'block';
    }
});
});


async function fetchComments() {
    try {
        const response = await fetch(`${API_URL}/comments/${LEAD_ID}`);
        const comments = await response.json();
        renderComments(comments);
    } catch (error) {
        console.error('Error fetching comments:', error);
    }
}

// Render comments
function renderComments(comments) {
    const container = document.getElementById('comments-container');
    container.innerHTML = comments.map(comment => `
        <div class="p-3 rounded-lg ${comment.is_internal ? 'bg-blue-50' : 'bg-gray-50'}">
            <div class="flex justify-between items-start mb-1">
                <span class="font-medium text-sm">${comment.author_name}</span>
                <span class="text-xs text-gray-500">
                    ${new Date(comment.created_at).toLocaleString('ru')}
                </span>
            </div>
            <p class="text-sm">${comment.text}</p>
            ${comment.is_internal ? 
                '<span class="text-xs text-blue-600 mt-1 inline-block">Внутренний комментарий</span>' 
                : ''}
        </div>
    `).join('');
}

// Add new comment
async function addComment(text, isInternal) {
    try {
        const response = await fetch(`/api/leads/comments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                lead_id: LEAD_ID,
                text: text,
                is_internal: isInternal
            })
        });
        
        if (response.ok) {
            fetchComments();
            document.getElementById('comment-input').value = '';
        }
    } catch (error) {
        console.error('Error adding comment:', error);
    }
}

// Event listeners
document.getElementById('send-comment').addEventListener('click', () => {
    const text = document.getElementById('comment-input').value.trim();
    const isInternal = document.getElementById('internal-comment').checked;
    
    if (text) {
        addComment(text, isInternal);
    }
});
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

document.querySelector('.fix-client').addEventListener("click", async() => {
    // Получаем кнопку "Фиксация клиента"
    const fixClientButton = document.querySelector('.fix-client');
 
        // Получаем lead_id из атрибута data-lead-id кнопки (замени на динамическое получение, если нужно)
        const leadId = fixClientButton.getAttribute('data-lead-id');

        if (!leadId) {
            showNotification("Ошибка: ID лида не найден. Проверьте данные.", "error");
            return;
        }

        // Данные для обновления лида (только state меняем на IN_WORK)
        const leadUpdateData = {
            state: "IN_WORK"
        };

        try {
            const response = await fetch(`/api/leads/${leadId}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(leadUpdateData),
            });

            const result = await response.json();
            if (response.ok) {
                showNotification("В работе!", "success");
                // Можно добавить дополнительные действия, например, обновление UI
            } else {
                console.error("Ошибка при обновлении лида:", result);
                showNotification("Ошибка: " + (result.detail || "Не удалось обновить статус лида"), "error");
            }
        } catch (error) {
            console.error("Ошибка сети:", error);
            showNotification("Ошибка сети! Проверьте подключение к серверу.", "error");
        }
});


// Initial load
fetchComments();



