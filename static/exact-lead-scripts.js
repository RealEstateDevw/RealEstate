"use strict";


const API_URL = '/api/leads';
const LEAD_ID = document.getElementById('leadId').value;


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

// Initial load
fetchComments();