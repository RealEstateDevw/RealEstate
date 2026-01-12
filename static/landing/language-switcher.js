// Система переключения языков для лендинга
class LanguageSwitcher {
    constructor() {
        this.currentLanguage = this.getStoredLanguage() || 'ru';
        this.translations = {
            ru: {
                // Header
                'header.contacts': 'Контакты',
                'header.conditions': 'Условия покупки',
                'header.pricing': 'Стоимость квартир',
                'header.select_apartment': 'Выбрать квартиру',
                'header.complex_rassvet': 'ЖК Рассвет',
                'header.complex_bahor': 'ЖК Бахор',
                
                // Hero section
                'hero.rassvet.name': 'ЖК «Рассвет»',
                'hero.rassvet.title': 'Пространство<br>света и комфорта',
                'hero.rassvet.features.1': '24 уникальных планировки',
                'hero.rassvet.features.2': 'Площади от 28 м² до 103 м²',
                'hero.rassvet.features.3': '6 блоков с современной архитектурой',
                'hero.rassvet.deadline': '4 Квартал<br>2026 года',
                
                'hero.bahor.name': 'ЖК «Бахор»',
                'hero.bahor.title': 'Пространство<br>света и комфорта',
                'hero.bahor.features.1': '18 уникальных планировок',
                'hero.bahor.features.2': 'Площади от 35 м² до 85 м²',
                'hero.bahor.features.3': '4 блока с современной архитектурой',
                'hero.bahor.deadline': '3 Квартал<br>2025 года',
                
                'hero.deadline_label': 'Срок сдачи',
                
                // Pricing section
                'pricing.title': 'Стоимость квартир',
                'pricing.all_apartments': 'Все квартиры',
                'pricing.rooms.1': '1 комната',
                'pricing.rooms.2': '2 комнаты',
                'pricing.rooms.3': '3 комнаты',
                'pricing.rooms.4': '4+ комнат',
                'pricing.loading': 'Загрузка квартир...',
                'pricing.no_apartments': 'Квартиры не найдены',
                'pricing.apartment_number': 'Номер квартиры',
                'pricing.area': 'Площадь',
                'pricing.rooms': 'Комнат',
                'pricing.floor': 'Этаж',
                'pricing.year': 'Год сдачи',
                'pricing.project': 'Проект',
                'pricing.price_per_m2': 'Цена за м²',
                'pricing.total_price': 'Общая стоимость',
                'pricing.remaining': 'Осталось всего',
                'pricing.apartments': 'квартир',
                'pricing.learn_more': 'Узнать подробнее',
                
                // Conditions section
                'conditions.title': 'Условия покупки — удобно и с выгодой',
                'conditions.installment.title': 'Рассрочка',
                'conditions.installment.desc': 'До 36 месяцев',
                'conditions.hybrid.title': 'Гибридная рассрочка',
                'conditions.hybrid.desc': 'С отложенным платежом до 30%',
                'conditions.mortgage.title': 'Переход на ипотеку',
                'conditions.mortgage.desc': 'В удобный момент без потерь',
                
                // Booking section
                'booking.title': 'Забронируйте свою квартиру уже сегодня',
                'booking.text': 'Выберите подходящий вариант, узнайте все детали и оформите бронь онлайн — просто и удобно',
                'booking.select_apartment': 'Выбрать квартиру',
                
                // Footer
                'footer.sales_offices': 'Отделы продаж',
                'footer.rassvet_office': 'г. Ташкент, ул. Навои, 15',
                'footer.rassvet_office_desc': '(Офис продаж ЖК «Рассвет»)',
                'footer.bahor_office': 'г. Ташкент, ул. Амира Темура, 25',
                'footer.bahor_office_desc': '(Офис продаж ЖК «Бахор»)',
                'footer.phone': 'Тел.:',
                'footer.show_on_map': 'Показать на карте',
                'footer.phone_title': 'Телефон',
                'footer.unified_line': 'Единая линия продаж',
                'footer.social_media': 'Мы в соцсетях',
                'footer.schedule': 'График работы',
                'footer.schedule_weekdays': 'Пн-Пт: 09:00 - 18:00',
                'footer.schedule_weekends': 'Сб-Вс: 10:00 - 16:00',
                'footer.email': 'Электронная почта',
                'footer.email_desc': 'Ответим в течение рабочего дня',
                'footer.note': 'Если у вас остались вопросы или вы хотите записаться на просмотр квартир, пожалуйста, позвоните нам или оставьте заявку на сайте — менеджер свяжется с вами в ближайшее время.',
                'footer.copyright': '© 2025 ISMConstructions. Все права защищены.',
                'footer.privacy_policy': 'Политика конфиденциальности',
                'footer.terms_of_service': 'Пользовательское соглашение',
                'footer.development': 'Разработка: внутренняя команда ISM',
                
                // Mobile menu
                'mobile_menu.contacts': 'Контакты',
                'mobile_menu.conditions': 'Условия покупки',
                'mobile_menu.pricing': 'Стоимость квартир',
                'mobile_menu.select_apartment': 'Выбрать квартиру',
                'mobile.select_complex': 'Выберите ЖК',
                'mobile.complex_rassvet': 'ЖК Рассвет',
                'mobile.complex_bahor': 'ЖК Бахор',
                
                // Complex selection
                'complex.rassvet': 'ЖК Рассвет',
                'complex.bahor': 'ЖК Бахор',
                
                // Header buttons
                'header.jk_rassvet': 'ЖК Рассвет',
                'header.jk_bahor': 'ЖК Бахор',
                
                // Pricing filters
                'pricing.non_residential': 'Не жилое',
                'pricing.1_room': '1 комната',
                'pricing.2_rooms': '2 комнаты',
                'pricing.3_rooms': '3 комнаты',
                'pricing.4_plus_rooms': '4+ комнат',
                
                // Language
                'lang.ru': 'RU',
                'lang.uz': 'UZ'
            },
            uz: {
                // Header
                'header.contacts': 'Aloqa',
                'header.conditions': 'Sotib olish shartlari',
                'header.pricing': 'Kvartira narxlari',
                'header.select_apartment': 'Kvartira tanlash',
                'header.complex_rassvet': 'JK "Tong"',
                'header.complex_bahor': 'JK "Bahor"',
                
                // Hero section
                'hero.rassvet.name': 'JK «Tong»',
                'hero.rassvet.title': 'Yorug\'lik va<br>qulaylik makoni',
                'hero.rassvet.features.1': '24 ta noyob rejalashtirish',
                'hero.rassvet.features.2': '28 m² dan 103 m² gacha maydon',
                'hero.rassvet.features.3': 'Zamonaviy arxitektura bilan 6 ta blok',
                'hero.rassvet.deadline': '2026 yil<br>4-chorak',
                
                'hero.bahor.name': 'JK «Bahor»',
                'hero.bahor.title': 'Yorug\'lik va<br>qulaylik makoni',
                'hero.bahor.features.1': '18 ta noyob rejalashtirish',
                'hero.bahor.features.2': '35 m² dan 85 m² gacha maydon',
                'hero.bahor.features.3': 'Zamonaviy arxitektura bilan 4 ta blok',
                'hero.bahor.deadline': '2025 yil<br>3-chorak',
                
                'hero.deadline_label': 'Topshirish muddati',
                
                // Pricing section
                'pricing.title': 'Kvartira narxlari',
                'pricing.all_apartments': 'Barcha kvartiralar',
                'pricing.rooms.1': '1 xona',
                'pricing.rooms.2': '2 xona',
                'pricing.rooms.3': '3 xona',
                'pricing.rooms.4': '4+ xona',
                'pricing.loading': 'Kvartiralar yuklanmoqda...',
                'pricing.no_apartments': 'Kvartiralar topilmadi',
                'pricing.apartment_number': 'Kvartira raqami',
                'pricing.area': 'Maydon',
                'pricing.rooms': 'Xonalar',
                'pricing.floor': 'Qavat',
                'pricing.year': 'Topshirish yili',
                'pricing.project': 'Loyiha',
                'pricing.price_per_m2': '1 m² uchun narx',
                'pricing.total_price': 'Umumiy qiymat',
                'pricing.remaining': 'Jami qoldi',
                'pricing.apartments': 'kvartira',
                'pricing.learn_more': 'Batafsil ma\'lumot',
                
                // Conditions section
                'conditions.title': 'Sotib olish shartlari — qulay va foydali',
                'conditions.installment.title': 'Bo\'lib to\'lash',
                'conditions.installment.desc': '24 oygacha',
                'conditions.hybrid.title': 'Gibrid bo\'lib to\'lash',
                'conditions.hybrid.desc': '30% gacha kechiktirilgan to\'lov bilan',
                'conditions.mortgage.title': 'Ipotekaga o\'tish',
                'conditions.mortgage.desc': 'Qulay vaqtda yo\'qotishsiz',
                
                // Booking section
                'booking.title': 'Bugun o\'z kvartirangizni bron qiling',
                'booking.text': 'Mos variantni tanlang, barcha tafsilotlarni bilib oling va onlayn bron qiling — oddiy va qulay',
                'booking.select_apartment': 'Kvartira tanlash',
                
                // Footer
                'footer.sales_offices': 'Sotish bo\'limlari',
                'footer.rassvet_office': 'Toshkent sh., Navoiy ko\'chasi, 15',
                'footer.rassvet_office_desc': '(JK «Tong» sotish ofisi)',
                'footer.bahor_office': 'Toshkent sh., Amir Temur ko\'chasi, 25',
                'footer.bahor_office_desc': '(JK «Bahor» sotish ofisi)',
                'footer.phone': 'Tel.:',
                'footer.show_on_map': 'Xaritada ko\'rsatish',
                'footer.phone_title': 'Telefon',
                'footer.unified_line': 'Yagona sotish liniyasi',
                'footer.social_media': 'Ijtimoiy tarmoqlarda',
                'footer.schedule': 'Ish jadvali',
                'footer.schedule_weekdays': 'Dush-Jum: 09:00 - 18:00',
                'footer.schedule_weekends': 'Shan-Yak: 10:00 - 16:00',
                'footer.email': 'Elektron pochta',
                'footer.email_desc': 'Ish kuni davomida javob beramiz',
                'footer.note': 'Agar sizda savollar qolgan bo\'lsa yoki kvartiralarni ko\'rish uchun ro\'yxatdan o\'tmoqchi bo\'lsangiz, iltimos, bizga qo\'ng\'iroq qiling yoki saytda ariza qoldiring — menejer tez orada siz bilan bog\'lanadi.',
                'footer.copyright': '© 2025 ISMConstructions. Barcha huquqlar himoyalangan.',
                'footer.privacy_policy': 'Maxfiylik siyosati',
                'footer.terms_of_service': 'Foydalanish shartlari',
                'footer.development': 'Ishlab chiqish: ISM ichki jamoasi',
                
                // Mobile menu
                'mobile_menu.contacts': 'Aloqa',
                'mobile_menu.conditions': 'Sotib olish shartlari',
                'mobile_menu.pricing': 'Kvartira narxlari',
                'mobile_menu.select_apartment': 'Kvartira tanlash',
                'mobile.select_complex': 'JK tanlang',
                'mobile.complex_rassvet': 'JK Tong',
                'mobile.complex_bahor': 'JK Bahor',
                
                // Complex selection
                'complex.rassvet': 'JK Tong',
                'complex.bahor': 'JK Bahor',
                
                // Header buttons
                'header.jk_rassvet': 'JK Tong',
                'header.jk_bahor': 'JK Bahor',
                
                // Pricing filters
                'pricing.non_residential': 'No-turar joy',
                'pricing.1_room': '1 xona',
                'pricing.2_rooms': '2 xona',
                'pricing.3_rooms': '3 xona',
                'pricing.4_plus_rooms': '4+ xona',
                
                // Language
                'lang.ru': 'RU',
                'lang.uz': 'UZ'
            }
        };
        
        this.init();
    }
    
    init() {
        this.createLanguageSwitcher();
        this.applyLanguage(this.currentLanguage);
        this.bindEvents();
    }
    
    getStoredLanguage() {
        return localStorage.getItem('landing_language');
    }
    
    setStoredLanguage(lang) {
        localStorage.setItem('landing_language', lang);
    }
    
    createLanguageSwitcher() {
        // Находим кнопку переключения языка в header
        const langButton = document.querySelector('.header-btn--lang');
        if (langButton) {
            langButton.addEventListener('click', () => {
                this.toggleLanguage();
            });
        }
    }
    
    toggleLanguage() {
        this.currentLanguage = this.currentLanguage === 'ru' ? 'uz' : 'ru';
        this.setStoredLanguage(this.currentLanguage);
        this.applyLanguage(this.currentLanguage);
    }
    
    getTranslation(key) {
        return this.translations[this.currentLanguage][key] || key;
    }
    
    applyLanguage(lang) {
        this.currentLanguage = lang;
        
        // Обновляем атрибут lang у html
        document.documentElement.lang = lang;
        
        // Обновляем все элементы с data-translate
        const elements = document.querySelectorAll('[data-translate]');
        elements.forEach(element => {
            const key = element.getAttribute('data-translate');
            const translation = this.getTranslation(key);
            
            if (element.tagName === 'INPUT' && element.type === 'text') {
                element.placeholder = translation;
            } else if (element.hasAttribute('title')) {
                element.title = translation;
            } else {
                element.textContent = translation;
            }
        });
        
        // Обновляем кнопку языка
        const langButton = document.querySelector('.header-btn--lang span');
        if (langButton) {
            langButton.textContent = this.getTranslation('lang.' + lang);
        }
        
        // Обновляем сложные элементы
        this.updateComplexElements();
    }
    
    updateComplexElements() {
        // Обновляем hero секцию
        this.updateHeroSection();
        
        // Обновляем условия покупки
        this.updateConditionsSection();
        
        // Обновляем footer
        this.updateFooterSection();
        
        // Обновляем мобильное меню
        this.updateMobileMenu();
    }
    
    updateHeroSection() {
        // Получаем текущий комплекс из body class
        const bodyClass = document.body.className;
        const isRassvet = bodyClass.includes('rassvet');
        const complexKey = isRassvet ? 'rassvet' : 'bahor';
        
        // Обновляем название ЖК
        const jkNameElement = document.querySelector('[data-role="hero-name"]');
        if (jkNameElement) {
            jkNameElement.textContent = this.getTranslation(`hero.${complexKey}.name`);
        }
        
        // Обновляем заголовок
        const titleElement = document.querySelector('[data-role="hero-title"]');
        if (titleElement) {
            titleElement.innerHTML = this.getTranslation(`hero.${complexKey}.title`);
        }
        
        // Обновляем особенности
        const featuresElement = document.querySelector('[data-role="hero-features"]');
        if (featuresElement) {
            const features = [
                this.getTranslation(`hero.${complexKey}.features.1`),
                this.getTranslation(`hero.${complexKey}.features.2`),
                this.getTranslation(`hero.${complexKey}.features.3`)
            ];
            featuresElement.innerHTML = features.map(feature => `<li>${feature}</li>`).join('');
        }
        
        // Обновляем срок сдачи
        const deadlineElement = document.querySelector('[data-role="hero-deadline"]');
        if (deadlineElement) {
            deadlineElement.innerHTML = this.getTranslation(`hero.${complexKey}.deadline`);
        }
        
        // Обновляем лейбл срока сдачи
        const deadlineLabelElement = document.querySelector('.hero__deadline-label');
        if (deadlineLabelElement) {
            deadlineLabelElement.textContent = this.getTranslation('hero.deadline_label');
        }
    }
    
    updateConditionsSection() {
        // Обновляем заголовок секции
        const sectionTitle = document.querySelector('#conditions .section__title');
        if (sectionTitle) {
            sectionTitle.textContent = this.getTranslation('conditions.title');
        }
        
        // Обновляем карточки условий
        const installmentCard = document.querySelector('[data-condition="installment"]');
        if (installmentCard) {
            const title = installmentCard.querySelector('.condition-card__title');
            const desc = installmentCard.querySelector('.condition-card__description');
            if (title) title.textContent = this.getTranslation('conditions.installment.title');
            if (desc) desc.textContent = this.getTranslation('conditions.installment.desc');
        }
        
        const hybridCard = document.querySelector('[data-condition="hybrid"]');
        if (hybridCard) {
            const title = hybridCard.querySelector('.condition-card__title');
            const desc = hybridCard.querySelector('.condition-card__description');
            if (title) title.textContent = this.getTranslation('conditions.hybrid.title');
            if (desc) desc.textContent = this.getTranslation('conditions.hybrid.desc');
        }
        
        const mortgageCard = document.querySelector('[data-condition="mortgage"]');
        if (mortgageCard) {
            const title = mortgageCard.querySelector('.condition-card__title');
            const desc = mortgageCard.querySelector('.condition-card__description');
            if (title) title.textContent = this.getTranslation('conditions.mortgage.title');
            if (desc) desc.textContent = this.getTranslation('conditions.mortgage.desc');
        }
    }
    
    updateFooterSection() {
        // Обновляем заголовок footer
        const footerTitle = document.querySelector('.footer-title');
        if (footerTitle) {
            footerTitle.textContent = this.getTranslation('footer.sales_offices');
        }
        
        // Обновляем адреса офисов
        const officeLocations = document.querySelectorAll('.footer-location');
        if (officeLocations.length >= 2) {
            // Первый офис (Рассвет)
            const rassvetOffice = officeLocations[0];
            const rassvetAddress = rassvetOffice.querySelector('p:first-child');
            const rassvetDesc = rassvetOffice.querySelector('p:nth-child(2)');
            if (rassvetAddress) rassvetAddress.textContent = this.getTranslation('footer.rassvet_office');
            if (rassvetDesc) rassvetDesc.textContent = this.getTranslation('footer.rassvet_office_desc');
            
            // Второй офис (Бахор)
            const bahorOffice = officeLocations[1];
            const bahorAddress = bahorOffice.querySelector('p:first-child');
            const bahorDesc = bahorOffice.querySelector('p:nth-child(2)');
            if (bahorAddress) bahorAddress.textContent = this.getTranslation('footer.bahor_office');
            if (bahorDesc) bahorDesc.textContent = this.getTranslation('footer.bahor_office_desc');
        }
        
        // Обновляем ссылки "Показать на карте"
        const mapLinks = document.querySelectorAll('.footer-location a');
        mapLinks.forEach(link => {
            const span = link.querySelector('span');
            if (span) {
                span.textContent = this.getTranslation('footer.show_on_map');
            }
        });
        
        // Обновляем секции footer
        const footerItems = document.querySelectorAll('.footer-item__title');
        footerItems.forEach((item, index) => {
            const titles = [
                'footer.phone_title',
                'footer.social_media',
                'footer.schedule',
                'footer.email'
            ];
            if (titles[index]) {
                item.textContent = this.getTranslation(titles[index]);
            }
        });
        
        // Обновляем расписание работы
        const scheduleItems = document.querySelectorAll('.footer-item__text p');
        scheduleItems.forEach((item, index) => {
            if (index === 0) item.textContent = this.getTranslation('footer.schedule_weekdays');
            if (index === 1) item.textContent = this.getTranslation('footer.schedule_weekends');
        });
        
        // Обновляем примечание
        const footerNote = document.querySelector('.footer-note');
        if (footerNote) {
            footerNote.textContent = this.getTranslation('footer.note');
        }
        
        // Обновляем копирайт
        const copyrightItems = document.querySelectorAll('.footer-copy p');
        if (copyrightItems.length >= 2) {
            copyrightItems[0].textContent = this.getTranslation('footer.copyright');
            copyrightItems[1].textContent = this.getTranslation('footer.development');
        }
    }
    
    updateMobileMenu() {
        // Обновляем лейбл выбора комплекса
        const complexLabel = document.querySelector('.mobile-complex-toggle__label');
        if (complexLabel) {
            complexLabel.textContent = this.getTranslation('mobile.select_complex');
        }
        
        // Обновляем кнопки комплексов в мобильном меню
        const complexButtons = document.querySelectorAll('.mobile-complex-toggle__btn');
        complexButtons.forEach(button => {
            const complex = button.getAttribute('data-complex');
            if (complex === 'rassvet') {
                button.textContent = this.getTranslation('mobile.complex_rassvet');
            } else if (complex === 'bahor') {
                button.textContent = this.getTranslation('mobile.complex_bahor');
            }
        });
    }
    
    bindEvents() {
        // Обработчик для переключения комплексов
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-role="complex-button"]')) {
                // Небольшая задержка для обновления после смены комплекса
                setTimeout(() => {
                    this.updateHeroSection();
                }, 100);
            }
        });
    }
}

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', () => {
    window.languageSwitcher = new LanguageSwitcher();
});
