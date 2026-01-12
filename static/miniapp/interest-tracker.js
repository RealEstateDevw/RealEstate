/**
 * Interest Tracker for Telegram Mini App
 *
 * Tracks user interest in apartments with anti-fraud measures:
 * - View count (+1 per view)
 * - Time score (+1 per 10 seconds, max +12)
 * - Event bonuses (payment view +3, map view +2, favorite +5)
 *
 * Anti-fraud:
 * - Only counts time when tab is visible
 * - Maximum 180 seconds per apartment
 * - Heartbeat every 10 seconds
 */

class InterestTracker {
    constructor(telegramId) {
        this.telegramId = telegramId;
        this.currentSessionId = null;
        this.currentScoreId = null;
        this.currentApartment = null;
        this.heartbeatInterval = null;
        this.lastHeartbeatTime = null;
        this.totalActiveSeconds = 0;
        this.isVisible = true;
        this.isActive = true;
        this.lastActivityTime = Date.now();

        // Constants
        this.HEARTBEAT_INTERVAL_MS = 10000; // 10 seconds
        this.MAX_SESSION_SECONDS = 180;
        this.INACTIVITY_TIMEOUT_MS = 30000; // 30 seconds

        this._setupVisibilityTracking();
        this._setupActivityTracking();

        console.log('[InterestTracker] Initialized for user:', telegramId);
    }

    /**
     * Setup visibility change tracking
     */
    _setupVisibilityTracking() {
        document.addEventListener('visibilitychange', () => {
            this.isVisible = document.visibilityState === 'visible';
            console.log('[InterestTracker] Visibility changed:', this.isVisible);

            if (this.isVisible && this.currentSessionId) {
                // Resume heartbeat when becoming visible
                this._startHeartbeat();
            } else if (!this.isVisible && this.heartbeatInterval) {
                // Pause heartbeat when hidden
                this._stopHeartbeat();
            }
        });
    }

    /**
     * Setup user activity tracking (mouse, keyboard, touch)
     */
    _setupActivityTracking() {
        const updateActivity = () => {
            this.isActive = true;
            this.lastActivityTime = Date.now();
        };

        document.addEventListener('mousemove', updateActivity);
        document.addEventListener('keydown', updateActivity);
        document.addEventListener('touchstart', updateActivity);
        document.addEventListener('scroll', updateActivity);
        document.addEventListener('click', updateActivity);

        // Check for inactivity periodically
        setInterval(() => {
            const inactiveTime = Date.now() - this.lastActivityTime;
            if (inactiveTime > this.INACTIVITY_TIMEOUT_MS) {
                this.isActive = false;
            }
        }, 5000);
    }

    /**
     * Start viewing session for an apartment
     * @param {Object} apartmentData - Apartment details
     */
    async startSession(apartmentData) {
        // End previous session if exists
        if (this.currentSessionId) {
            await this.endSession();
        }

        console.log('[InterestTracker] Starting session for:', apartmentData);

        try {
            const response = await fetch('/api/miniapp/view-session/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    telegram_id: this.telegramId,
                    complex_name: apartmentData.complexName,
                    block_name: apartmentData.blockName,
                    floor: parseInt(apartmentData.floor, 10),
                    unit_number: String(apartmentData.unitNumber),
                    area_sqm: apartmentData.areaSqm ? parseFloat(String(apartmentData.areaSqm).replace(',', '.')) : null,
                    rooms: apartmentData.rooms ? parseInt(apartmentData.rooms, 10) : null
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.currentSessionId = data.session_id;
            this.currentScoreId = data.score_id;
            this.currentApartment = apartmentData;
            this.totalActiveSeconds = 0;
            this.lastHeartbeatTime = Date.now();

            console.log('[InterestTracker] Session started:', data);

            // Start heartbeat
            this._startHeartbeat();

            return data;
        } catch (error) {
            console.error('[InterestTracker] Failed to start session:', error);
            return null;
        }
    }

    /**
     * Start heartbeat interval
     */
    _startHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }

        this.lastHeartbeatTime = Date.now();

        this.heartbeatInterval = setInterval(() => {
            this._sendHeartbeat();
        }, this.HEARTBEAT_INTERVAL_MS);
    }

    /**
     * Stop heartbeat interval
     */
    _stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    /**
     * Send heartbeat to API
     */
    async _sendHeartbeat() {
        if (!this.currentSessionId) {
            return;
        }

        // Only count time if visible AND active
        if (!this.isVisible || !this.isActive) {
            console.log('[InterestTracker] Skipping heartbeat - not visible or active');
            return;
        }

        // Calculate seconds since last heartbeat (max 30 to prevent abuse)
        const now = Date.now();
        const secondsElapsed = Math.min(
            Math.floor((now - this.lastHeartbeatTime) / 1000),
            30
        );
        this.lastHeartbeatTime = now;

        if (secondsElapsed < 1) {
            return;
        }

        try {
            const response = await fetch('/api/miniapp/view-session/heartbeat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.currentSessionId,
                    telegram_id: this.telegramId,
                    seconds_elapsed: secondsElapsed,
                    is_visible: this.isVisible
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.totalActiveSeconds = data.total_active_seconds;

            console.log('[InterestTracker] Heartbeat sent, total time:', this.totalActiveSeconds);

            // Check if we should end session (cap reached)
            if (data.should_end || this.totalActiveSeconds >= this.MAX_SESSION_SECONDS) {
                console.log('[InterestTracker] Max time reached, ending session');
                this._stopHeartbeat();
            }

            return data;
        } catch (error) {
            console.error('[InterestTracker] Heartbeat error:', error);
        }
    }

    /**
     * Record an interest event (payment view, map view)
     * @param {string} eventType - 'payment_view' or 'map_view'
     */
    async recordEvent(eventType) {
        if (!this.currentApartment) {
            console.warn('[InterestTracker] No current apartment for event');
            return null;
        }

        console.log('[InterestTracker] Recording event:', eventType);

        try {
            const response = await fetch('/api/miniapp/interest-event', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    telegram_id: this.telegramId,
                    complex_name: this.currentApartment.complexName,
                    block_name: this.currentApartment.blockName,
                    floor: parseInt(this.currentApartment.floor, 10),
                    unit_number: String(this.currentApartment.unitNumber),
                    event_type: eventType
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            console.log('[InterestTracker] Event recorded:', data);
            return data;
        } catch (error) {
            console.error('[InterestTracker] Failed to record event:', error);
            return null;
        }
    }

    /**
     * End current viewing session
     */
    async endSession() {
        if (!this.currentSessionId) {
            return null;
        }

        this._stopHeartbeat();

        console.log('[InterestTracker] Ending session:', this.currentSessionId);

        try {
            const response = await fetch('/api/miniapp/view-session/end', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.currentSessionId,
                    telegram_id: this.telegramId
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            console.log('[InterestTracker] Session ended:', data);

            // Reset state
            this.currentSessionId = null;
            this.currentScoreId = null;
            this.currentApartment = null;
            this.totalActiveSeconds = 0;

            return data;
        } catch (error) {
            console.error('[InterestTracker] Failed to end session:', error);
            // Reset state anyway
            this.currentSessionId = null;
            this.currentScoreId = null;
            this.currentApartment = null;
            return null;
        }
    }

    /**
     * Get current session info
     */
    getSessionInfo() {
        return {
            sessionId: this.currentSessionId,
            scoreId: this.currentScoreId,
            apartment: this.currentApartment,
            totalActiveSeconds: this.totalActiveSeconds,
            isVisible: this.isVisible,
            isActive: this.isActive
        };
    }
}

// Export to window
window.InterestTracker = InterestTracker;
