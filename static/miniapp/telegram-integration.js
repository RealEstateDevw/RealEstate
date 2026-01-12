/**
 * Telegram Mini App Integration
 *
 * This file handles:
 * - Detection of Mini App vs regular browser context
 * - User initialization with Telegram data
 * - Theme application
 * - API communication for lead requests
 */

// ===== CONTEXT DETECTION =====
window.isTelegramMiniApp = !!(window.Telegram?.WebApp?.initData);
window.interestTracker = null;
window.miniAppUser = null;

// ===== INITIALIZATION (Mini App only) =====
if (window.isTelegramMiniApp) {
    const tg = window.Telegram.WebApp;

    // Signal that Mini App is ready
    tg.ready();

    // Expand to full height
    tg.expand();

    // Get payload from deep link (ad source tracking)
    const startParam = tg.initDataUnsafe?.start_param || 'telegram';
    const telegramId = tg.initDataUnsafe?.user?.id;

    console.log('[MiniApp] Initialized with payload:', startParam, 'telegramId:', telegramId);

    // Initialize user in API
    initMiniAppUser(tg.initData, startParam).then(user => {
        window.miniAppUser = user;
        console.log('[MiniApp] User initialized:', user);

        // Create interest tracker (Mini App only)
        if (typeof InterestTracker !== 'undefined' && telegramId) {
            window.interestTracker = new InterestTracker(telegramId);
            console.log('[MiniApp] Interest tracker created');
        }
    }).catch(err => {
        console.error('[MiniApp] Failed to init user:', err);
    });

    // Apply Telegram theme
    applyTelegramTheme(tg);

    // Handle back button
    tg.BackButton.onClick(() => {
        window.history.back();
    });

    // Show back button when navigating
    window.addEventListener('popstate', () => {
        if (window.history.length > 1) {
            tg.BackButton.show();
        } else {
            tg.BackButton.hide();
        }
    });
}

// ===== THEME APPLICATION =====
function applyTelegramTheme(tg) {
    const root = document.documentElement;

    // Set CSS custom properties from Telegram theme
    if (tg.themeParams) {
        root.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color || '#ffffff');
        root.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color || '#000000');
        root.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color || '#999999');
        root.style.setProperty('--tg-theme-link-color', tg.themeParams.link_color || '#2481cc');
        root.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color || '#2481cc');
        root.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color || '#ffffff');
        root.style.setProperty('--tg-theme-secondary-bg-color', tg.themeParams.secondary_bg_color || '#f0f0f0');
    }

    // Add class to body for CSS targeting
    document.body.classList.add('telegram-miniapp');
}

// ===== API FUNCTIONS =====

/**
 * Initialize Mini App user
 * @param {string} initData - Telegram initData string
 * @param {string} startParam - Payload from deep link
 * @returns {Promise<Object>} User data
 */
async function initMiniAppUser(initData, startParam) {
    try {
        const response = await fetch('/api/miniapp/init', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                init_data: initData,
                start_param: startParam
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('[MiniApp] initMiniAppUser error:', error);
        throw error;
    }
}

/**
 * Create lead request from Mini App
 * @param {Object} data - Lead request data
 * @returns {Promise<Object>} Created request
 */
async function createLeadRequest(data) {
    const telegramId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;

    if (!telegramId) {
        console.error('[MiniApp] No telegram ID for lead request');
        return null;
    }

    try {
        const response = await fetch('/api/miniapp/lead-request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: telegramId,
                ...data
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('[MiniApp] createLeadRequest error:', error);
        throw error;
    }
}

/**
 * Add apartment to favorites
 * @param {Object} apartmentData - Apartment details
 * @returns {Promise<Object>} Result
 */
async function addToFavorites(apartmentData) {
    const telegramId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;

    if (!telegramId) {
        console.error('[MiniApp] No telegram ID for favorites');
        return null;
    }

    try {
        const response = await fetch('/api/miniapp/favorites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: telegramId,
                ...apartmentData
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('[MiniApp] addToFavorites error:', error);
        throw error;
    }
}

/**
 * Remove apartment from favorites
 * @param {Object} apartmentData - Apartment details
 * @returns {Promise<Object>} Result
 */
async function removeFromFavorites(apartmentData) {
    const telegramId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;

    if (!telegramId) {
        return null;
    }

    try {
        const response = await fetch('/api/miniapp/favorites', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: telegramId,
                ...apartmentData
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('[MiniApp] removeFromFavorites error:', error);
        throw error;
    }
}

// ===== CLEANUP ON PAGE UNLOAD =====
window.addEventListener('beforeunload', () => {
    if (window.interestTracker && window.interestTracker.currentSessionId) {
        // Use sendBeacon for reliable delivery on page unload
        const data = JSON.stringify({
            session_id: window.interestTracker.currentSessionId,
            telegram_id: window.Telegram?.WebApp?.initDataUnsafe?.user?.id
        });

        navigator.sendBeacon('/api/miniapp/view-session/end', data);
    }
});

// ===== EXPORT FOR GLOBAL ACCESS =====
window.MiniAppAPI = {
    initUser: initMiniAppUser,
    createLeadRequest: createLeadRequest,
    addToFavorites: addToFavorites,
    removeFromFavorites: removeFromFavorites
};
