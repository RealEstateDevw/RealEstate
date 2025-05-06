function openModalNot(leadId) {
    const modal = document.getElementById('callbackModal');
    modal.style.display = 'flex';
    window.currentLeadId = leadId; // Store the lead ID for later use
}

function closeModalNot() {
    const modal = document.getElementById('callbackModal');
    modal.style.display = 'none';
}






// async function saveCallbackTime() {
//     const callbackTime = document.getElementById('callbackTime').value;
//     const leadId = window.currentLeadId;

//     if (!callbackTime || !leadId) {
//         showNotification('Пожалуйста, выберите время и убедитесь, что лид выбран.', 'error');
//         return;
//     }

//     try {
//         const response = await fetch(`/api/leads/${leadId}/schedule-callback`, {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify({ callbackTime }),
//         });

//         if (!response.ok) throw new Error('Ошибка при сохранении времени звонка');
        
//         showNotification('Напоминание успешно запланировано!', 'success');
//         closeModalNot(); // Refresh the lead list to reflect the update
//     } catch (error) {
//         console.error('Ошибка:', error);
//         showNotification('Произошла ошибка при сохранении времени.', 'error');
//     }
// }