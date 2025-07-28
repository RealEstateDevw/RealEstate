"use strict";


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
        const response = await fetch(`/api/finance/search?query=${encodeURIComponent(query)}&limit=10`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (!data) {
                throw new Error('Получены пустые данные');
            }


        displayResults(data);
    } catch (error) {
        console.error('Ошибка при поиске:', error);
        searchResults.innerHTML = '<div class="no-results">Произошла ошибка при загрузке данных</div>';
        searchResults.style.display = 'block';
    }
});
});

function displayResults(data) {
    const searchResults = document.getElementById('searchResults');
    searchResults.innerHTML = '';  // Очищаем список результатов

    // Проверяем, есть ли результаты
    if (!data || !data.results || data.results.length === 0) {
        searchResults.innerHTML = '<div class="no-results">Нет результатов</div>';
        searchResults.style.display = 'block';
        return;
    }

    // Перебираем результаты
    data.results.forEach(result => {
        const item = document.createElement('div');
        item.classList.add('result-item');

        // Определяем тип и иконку
        let roleDisplay, roleIcon, detailUrl;

        if (result.type === 'user') {
            roleDisplay = 'Продажник';
            roleIcon = '<i class="fas fa-user-tie"></i>';
            detailUrl = `/users/${result.id}`;
        } else if (result.type === 'lead') {
            roleDisplay = 'Лид';
            roleIcon = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"><path fill-rule="evenodd" clip-rule="evenodd" d="M10 4H14C17.7712 4 19.6569 4 20.8284 5.17157C22 6.34315 22 8.22876 22 12C22 15.7712 22 17.6569 20.8284 18.8284C19.6569 20 17.7712 20 14 20H10C6.22876 20 4.34315 20 3.17157 18.8284C2 17.6569 2 15.7712 2 12C2 8.22876 2 6.34315 3.17157 5.17157C4.34315 4 6.22876 4 10 4ZM13.25 9C13.25 8.58579 13.5858 8.25 14 8.25H19C19.4142 8.25 19.75 8.58579 19.75 9C19.75 9.41421 19.4142 9.75 19 9.75H14C13.5858 9.75 13.25 9.41421 13.25 9ZM14.25 12C14.25 11.5858 14.5858 11.25 15 11.25H19C19.4142 11.25 19.75 11.5858 19.75 12C19.75 12.4142 19.4142 12.75 19 12.75H15C14.5858 12.75 14.25 12.4142 14.25 12ZM15.25 15C15.25 14.5858 15.5858 14.25 16 14.25H19C19.4142 14.25 19.75 14.5858 19.75 15C19.75 15.4142 19.4142 15.75 19 15.75H16C15.5858 15.75 15.25 15.4142 15.25 15ZM11 9C11 10.1046 10.1046 11 9 11C7.89543 11 7 10.1046 7 9C7 7.89543 7.89543 7 9 7C10.1046 7 11 7.89543 11 9ZM9 17C13 17 13 16.1046 13 15C13 13.8954 11.2091 13 9 13C6.79086 13 5 13.8954 5 15C5 16.1046 5 17 9 17Z" fill="#216BF4"/></svg>';
            detailUrl = `/leads/${result.id}`;
        } else if (result.type === 'expense') {
            roleDisplay = 'Выплата';
            roleIcon = '<i class="fas fa-money-bill-wave"></i>';
            detailUrl = `/expenses/${result.id}`;
        }

        // Формируем HTML
        item.innerHTML = `
            <div class="result-name">${result.name}</div>
            <div class="result-role">
                ${roleIcon}
                ${roleDisplay}
            </div>
        `;

        // Добавляем обработчик клика
        item.addEventListener('click', () => {
            window.location.href = detailUrl;
        });

        searchResults.appendChild(item);
    });

    searchResults.style.display = 'block';
}