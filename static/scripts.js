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

    