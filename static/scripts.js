"use strict";


     
        document.querySelectorAll('.icon-edit').forEach((icon) => {
            icon.addEventListener('click', function () {
                // Находим соседний input в том же контейнере (form-update)
                const input = this.closest('.form-update').querySelector('input.dynamicInput');
                
                // Снимаем атрибут readonly и устанавливаем фокус на поле ввода
                if (input) {
                    if (input) {
                    // Сохраняем исходное значение, если это не сделано заранее
                    if (!input.hasAttribute('data-original')) {
                        input.setAttribute('data-original', input.value);
                    }

                    // Снимаем атрибут readonly и устанавливаем фокус
                    input.removeAttribute('readonly');
                    input.focus();

                    // Обрабатываем событие потери фокуса (blur)
                    input.addEventListener('blur', () => {
                        if (input.value.trim() === '') {
                            // Возвращаем исходное значение, если поле пустое
                            input.value = input.getAttribute('data-original');
                        }
                        // Возвращаем атрибут readonly
                        input.setAttribute('readonly', true);
                    }, { once: true });  // once: true — обрабатываем blur только один раз
                }
                }
            });
        });
        document.querySelectorAll('.icon-profile').forEach(icon => {
            icon.addEventListener('click', () => {
                const input = icon.closest('.info-card-profile').querySelector('.text-profile');

                if (input) {
                    // Сохраняем исходное значение, если это не сделано заранее
                    if (!input.hasAttribute('data-original')) {
                        input.setAttribute('data-original', input.value);
                    }

                    // Снимаем атрибут readonly и устанавливаем фокус
                    input.removeAttribute('readonly');
                    input.focus();

                    // Обрабатываем событие потери фокуса (blur)
                    input.addEventListener('blur', () => {
                        if (input.value.trim() === '') {
                            // Возвращаем исходное значение, если поле пустое
                            input.value = input.getAttribute('data-original');
                        }
                        // Возвращаем атрибут readonly
                        input.setAttribute('readonly', true);
                    }, { once: true });  // once: true — обрабатываем blur только один раз
                }
            });
        });

        async function filterEmployees() {
            const roleId = document.getElementById('roleFilter').value;
        
            try {
                // Формируем URL с параметром role_id
                const response = await fetch(`/api/users/employees${roleId ? `?role_id=${roleId}` : ''}`);
                const employees = await response.json();
        
                // Очищаем текущий список сотрудников
                const employeeList = document.querySelector('.employee-list');
                employeeList.innerHTML = '';
        
                // Генерируем новый список сотрудников
                employees.forEach(user => {
                    const workStatus = user.work_status === 'Рабочий' && user.checkin_time
                        ? `<span style="color: green; font-size: 12px;">●</span> Был на работе`
                        : user.work_status === 'Выходной'
                        ? `<span style="color: gray; font-size: 12px;">●</span> Выходной`
                        : `<span style="color: red; font-size: 12px;">●</span> Отсутствовал`;
                    const employeeItem = `
                        <div class="employee-item" onclick=showUserDetails(${user.id}) data-user-id="${user.id}" data-user-id-main="${user.id}">
                            <div class="employee-name">
                                ${user.last_name} ${user.first_name}
                                <div class="status">
                                    ${workStatus}
                                    <i class="fas fa-chevron-right"></i>
                                </div>
                            </div>
                            <div class="employee-position">${user.role.name || 'Без должности'}</div>
                        </div>
                    `;
        
                    employeeList.innerHTML += employeeItem;
                });
        
            } catch (error) {
                console.error('Ошибка при фильтрации сотрудников:', error);
            }
        }
        async function loadRoles() {
            try {
                const response = await fetch('/api/users/roles');
                const roles = await response.json();
        
                const roleFilter = document.getElementById('roleFilter');
                
                // Заполняем список ролей
                roles.forEach(role => {
                    const option = document.createElement('option');
                    option.value = role.id;  // Используем ID роли
                    option.textContent = role.name;
                    roleFilter.appendChild(option);
                });
        
            } catch (error) {
                console.error('Ошибка при загрузке ролей:', error);
            }
        }
        window.onload = () => {
            filterEmployees();
            loadRoles();
        };