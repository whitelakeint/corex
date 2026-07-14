/**
 * State Machine for Kiosk Conversation Flow
 * Manages transitions between IDLE, STARTING, ACTIVE, ENDING, ERROR states
 */

class ConversationStateMachine {
  constructor(config = {}) {
    this.config = {
      faceDetectedDelay: config.faceDetectedDelay || 1500, // 1.5 seconds
      faceGoneDelay: config.faceGoneDelay || 10000, // 10 seconds
      errorRecoveryDelay: config.errorRecoveryDelay || 5000, // 5 seconds
      ...config
    };

    this.currentState = 'IDLE';
    this.previousState = null;
    this.conversationId = null;

    // Timers
    this.faceDetectedStartTime = null;
    this.faceGoneStartTime = null;
    this.errorRecoveryTimeout = null;

    // Callbacks
    this.onStateChange = null;
    this.onStartConversation = null;
    this.onEndConversation = null;
  }

  /**
   * Get current state
   * @returns {string} Current state
   */
  getState() {
    return this.currentState;
  }

  /**
   * Set state change callback
   * @param {Function} callback - Called with (newState, oldState)
   */
  setStateChangeCallback(callback) {
    this.onStateChange = callback;
  }

  /**
   * Set conversation start callback
   * @param {Function} callback - Called when conversation should start
   */
  setStartConversationCallback(callback) {
    this.onStartConversation = callback;
  }

  /**
   * Set conversation end callback
   * @param {Function} callback - Called with conversationId
   */
  setEndConversationCallback(callback) {
    this.onEndConversation = callback;
  }

  /**
   * Transition to new state
   * @param {string} newState - Target state
   */
  setState(newState) {
    if (this.currentState === newState) return;

    console.log(`[StateMachine] ${this.currentState} → ${newState}`);

    this.previousState = this.currentState;
    this.currentState = newState;

    // Call state change callback
    if (this.onStateChange) {
      this.onStateChange(newState, this.previousState);
    }

    // Execute state entry logic
    this.onStateEnter(newState);
  }

  /**
   * Handle state entry
   * @param {string} state - Entered state
   */
  onStateEnter(state) {
    switch (state) {
      case 'IDLE':
        this.enterIdleState();
        break;

      case 'STARTING_CONVERSATION':
        this.enterStartingState();
        break;

      case 'CONVERSATION_ACTIVE':
        this.enterActiveState();
        break;

      case 'ENDING_CONVERSATION':
        this.enterEndingState();
        break;

      case 'ERROR_RECOVERY':
        this.enterErrorRecoveryState();
        break;
    }
  }

  /**
   * Enter IDLE state
   */
  enterIdleState() {
    this.conversationId = null;
    this.faceDetectedStartTime = null;
    this.faceGoneStartTime = null;

    if (this.errorRecoveryTimeout) {
      clearTimeout(this.errorRecoveryTimeout);
      this.errorRecoveryTimeout = null;
    }
  }

  /**
   * Enter STARTING_CONVERSATION state
   */
  enterStartingState() {
    if (this.onStartConversation) {
      this.onStartConversation()
        .then(conversationId => {
          this.conversationId = conversationId;
          this.setState('CONVERSATION_ACTIVE');
        })
        .catch(error => {
          console.error('[StateMachine] Failed to start conversation:', error);

          // Check if this is a retryable error (service unavailable)
          if (error.retryAfter) {
            const retryMs = error.retryAfter * 1000;
            console.log(`[StateMachine] Will retry in ${error.retryAfter}s`);

            // Schedule retry - go to IDLE and the face detection will retry naturally
            setTimeout(() => {
              console.log('[StateMachine] Retry timeout elapsed, returning to IDLE');
              this.setState('IDLE');
            }, retryMs);

            // Don't go to ERROR_RECOVERY - just wait
            return;
          }

          this.setState('ERROR_RECOVERY');
        });
    }
  }

  /**
   * Enter CONVERSATION_ACTIVE state
   */
  enterActiveState() {
    this.faceGoneStartTime = null;
  }

  /**
   * Enter ENDING_CONVERSATION state
   */
  enterEndingState() {
    if (this.onEndConversation && this.conversationId) {
      this.onEndConversation(this.conversationId)
        .then(() => {
          this.setState('IDLE');
        })
        .catch(error => {
          console.error('[StateMachine] Failed to end conversation:', error);
          // Still return to IDLE even if end call fails
          this.setState('IDLE');
        });
    } else {
      // No conversation to end, go directly to IDLE
      this.setState('IDLE');
    }
  }

  /**
   * Enter ERROR_RECOVERY state
   */
  enterErrorRecoveryState() {
    // Auto-return to IDLE after delay
    this.errorRecoveryTimeout = setTimeout(() => {
      this.setState('IDLE');
    }, this.config.errorRecoveryDelay);
  }

  /**
   * Handle face detection result
   * @param {boolean} facePresent - Whether face(s) detected
   * @param {number} faceCount - Number of faces detected
   */
  handleFaceDetection(facePresent, faceCount = 0) {
    const now = Date.now();

    switch (this.currentState) {
      case 'IDLE':
        this.handleIdleDetection(facePresent, now);
        break;

      case 'CONVERSATION_ACTIVE':
        this.handleActiveDetection(facePresent, now);
        break;

      // Ignore face detection during transitions
      case 'STARTING_CONVERSATION':
      case 'ENDING_CONVERSATION':
      case 'ERROR_RECOVERY':
        break;
    }
  }

  /**
   * Handle detection during IDLE state
   * @param {boolean} facePresent - Face detected
   * @param {number} now - Current timestamp
   */
  handleIdleDetection(facePresent, now) {
    if (facePresent) {
      // Start or continue timer
      if (!this.faceDetectedStartTime) {
        this.faceDetectedStartTime = now;
        console.log('[StateMachine] Face detected, starting timer');
      } else {
        const elapsed = now - this.faceDetectedStartTime;
        if (elapsed >= this.config.faceDetectedDelay) {
          console.log(`[StateMachine] Face present for ${elapsed}ms, starting conversation`);
          this.setState('STARTING_CONVERSATION');
        }
      }
    } else {
      // Reset timer if face lost
      if (this.faceDetectedStartTime) {
        console.log('[StateMachine] Face lost, resetting timer');
        this.faceDetectedStartTime = null;
      }
    }
  }

  /**
   * Handle detection during CONVERSATION_ACTIVE state
   * @param {boolean} facePresent - Face detected
   * @param {number} now - Current timestamp
   */
  handleActiveDetection(facePresent, now) {
    if (facePresent) {
      // Reset absence timer if face present
      if (this.faceGoneStartTime) {
        console.log('[StateMachine] Face returned, resetting absence timer');
        this.faceGoneStartTime = null;
      }
    } else {
      // Start or continue absence timer
      if (!this.faceGoneStartTime) {
        this.faceGoneStartTime = now;
        console.log('[StateMachine] Face gone, starting absence timer');
      } else {
        const elapsed = now - this.faceGoneStartTime;
        if (elapsed >= this.config.faceGoneDelay) {
          console.log(`[StateMachine] Face absent for ${elapsed}ms, ending conversation`);
          this.setState('ENDING_CONVERSATION');
        }
      }
    }
  }

  /**
   * Manually trigger conversation start (for testing/override)
   */
  forceStartConversation() {
    if (this.currentState === 'IDLE') {
      this.setState('STARTING_CONVERSATION');
    }
  }

  /**
   * Manually trigger conversation end (for testing/override)
   */
  forceEndConversation() {
    if (this.currentState === 'CONVERSATION_ACTIVE') {
      this.setState('ENDING_CONVERSATION');
    }
  }

  /**
   * Get timer status for debugging
   * @returns {Object} Timer information
   */
  getTimerStatus() {
    const now = Date.now();
    return {
      state: this.currentState,
      faceDetectedTimer: this.faceDetectedStartTime
        ? now - this.faceDetectedStartTime
        : null,
      faceGoneTimer: this.faceGoneStartTime
        ? now - this.faceGoneStartTime
        : null,
      conversationId: this.conversationId
    };
  }

  /**
   * Clean up resources
   */
  dispose() {
    if (this.errorRecoveryTimeout) {
      clearTimeout(this.errorRecoveryTimeout);
    }
    this.onStateChange = null;
    this.onStartConversation = null;
    this.onEndConversation = null;
  }
}

// Export for use in index.html
window.ConversationStateMachine = ConversationStateMachine;
