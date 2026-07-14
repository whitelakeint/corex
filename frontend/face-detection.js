/**
 * Face Detection Module
 * Uses TensorFlow.js BlazeFace model for real-time face detection
 */

class FaceDetectionManager {
  constructor(config = {}) {
    this.config = {
      minConfidence: config.minConfidence || 0.75,
      minFaceSize: config.minFaceSize || 0.15,
      idleFps: config.idleFps || 5,
      activeFps: config.activeFps || 2,
      canvasWidth: config.canvasWidth || 640,
      canvasHeight: config.canvasHeight || 480,
      ...config
    };

    this.model = null;
    this.cameraStream = null;
    this.videoElement = null;
    this.canvasElement = null;
    this.ctx = null;
    this.isDetecting = false;
    this.detectionCallback = null;
    this.currentFps = this.config.idleFps;
    this.inferenceTimeHistory = [];
  }

  /**
   * Initialize camera access
   * @returns {Promise<boolean>} Success status
   */
  async initCamera() {
    try {
      console.log('[FaceDetection] Requesting camera access...');

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        },
        audio: false
      });

      this.cameraStream = stream;

      // Set up video element
      this.videoElement = document.getElementById('camera-feed');
      if (!this.videoElement) {
        throw new Error('Camera feed element not found');
      }

      this.videoElement.srcObject = stream;
      await this.videoElement.play();

      // Set up canvas for detection
      this.canvasElement = document.getElementById('detection-canvas');
      if (!this.canvasElement) {
        throw new Error('Detection canvas element not found');
      }

      this.canvasElement.width = this.config.canvasWidth;
      this.canvasElement.height = this.config.canvasHeight;
      this.ctx = this.canvasElement.getContext('2d');

      console.log('[FaceDetection] Camera initialized successfully');
      return true;

    } catch (error) {
      console.error('[FaceDetection] Camera access failed:', error);
      return false;
    }
  }

  /**
   * Load BlazeFace model
   * @returns {Promise<boolean>} Success status
   */
  async loadModel() {
    try {
      console.log('[FaceDetection] Loading BlazeFace model...');

      // Set backend to WebGL for GPU acceleration
      await tf.setBackend('webgl');
      await tf.ready();

      // Load BlazeFace model
      this.model = await blazeface.load();

      // Warm up model with dummy inference
      await this.warmUpModel();

      console.log('[FaceDetection] Model loaded successfully');
      return true;

    } catch (error) {
      console.error('[FaceDetection] Model loading failed:', error);
      return false;
    }
  }

  /**
   * Warm up model with dummy inference
   */
  async warmUpModel() {
    const dummyCanvas = document.createElement('canvas');
    dummyCanvas.width = this.config.canvasWidth;
    dummyCanvas.height = this.config.canvasHeight;
    await this.model.estimateFaces(dummyCanvas, false);
    console.log('[FaceDetection] Model warmed up');
  }

  /**
   * Start detection loop
   * @param {Function} callback - Called with boolean indicating face presence
   * @param {string} mode - 'idle' or 'active' (affects FPS)
   */
  startDetection(callback, mode = 'idle') {
    if (!this.model || !this.cameraStream) {
      console.error('[FaceDetection] Cannot start detection: model or camera not ready');
      return;
    }

    this.isDetecting = true;
    this.detectionCallback = callback;
    this.currentFps = mode === 'idle' ? this.config.idleFps : this.config.activeFps;

    console.log(`[FaceDetection] Starting detection at ${this.currentFps} FPS`);
    this.detectLoop();
  }

  /**
   * Stop detection loop
   */
  stopDetection() {
    this.isDetecting = false;
    this.detectionCallback = null;
    console.log('[FaceDetection] Detection stopped');
  }

  /**
   * Update detection FPS
   * @param {string} mode - 'idle' or 'active'
   */
  setDetectionMode(mode) {
    this.currentFps = mode === 'idle' ? this.config.idleFps : this.config.activeFps;
    console.log(`[FaceDetection] Detection mode set to ${mode} (${this.currentFps} FPS)`);
  }

  /**
   * Main detection loop
   */
  async detectLoop() {
    if (!this.isDetecting) return;

    const startTime = performance.now();

    try {
      // Draw current video frame to canvas
      this.ctx.drawImage(
        this.videoElement,
        0, 0,
        this.config.canvasWidth,
        this.config.canvasHeight
      );

      // Run face detection
      const predictions = await this.model.estimateFaces(this.canvasElement, false);

      // Filter valid faces
      const validFaces = this.filterValidFaces(predictions);

      // Call callback with result
      if (this.detectionCallback) {
        this.detectionCallback(validFaces.length > 0, validFaces.length);
      }

      // Track inference time
      const inferenceTime = performance.now() - startTime;
      this.trackInferenceTime(inferenceTime);

    } catch (error) {
      console.error('[FaceDetection] Detection error:', error);
    }

    // Schedule next detection
    const elapsed = performance.now() - startTime;
    const interval = 1000 / this.currentFps;
    const nextDelay = Math.max(0, interval - elapsed);

    setTimeout(() => this.detectLoop(), nextDelay);
  }

  /**
   * Filter predictions by confidence and size
   * @param {Array} predictions - BlazeFace predictions
   * @returns {Array} Valid face predictions
   */
  filterValidFaces(predictions) {
    if (!predictions || predictions.length === 0) {
      return [];
    }

    return predictions.filter(pred => {
      // Check confidence
      const confidence = pred.probability ? pred.probability[0] : 0;
      if (confidence < this.config.minConfidence) {
        return false;
      }

      // Check face size (relative to canvas)
      const faceWidth = pred.bottomRight[0] - pred.topLeft[0];
      const relativeSize = faceWidth / this.config.canvasWidth;

      if (relativeSize < this.config.minFaceSize) {
        return false;
      }

      return true;
    });
  }

  /**
   * Track inference time for performance monitoring
   * @param {number} time - Inference time in ms
   */
  trackInferenceTime(time) {
    this.inferenceTimeHistory.push(time);
    if (this.inferenceTimeHistory.length > 30) {
      this.inferenceTimeHistory.shift();
    }
  }

  /**
   * Get average inference time
   * @returns {number} Average inference time in ms
   */
  getAverageInferenceTime() {
    if (this.inferenceTimeHistory.length === 0) return 0;
    const sum = this.inferenceTimeHistory.reduce((a, b) => a + b, 0);
    return sum / this.inferenceTimeHistory.length;
  }

  /**
   * Clean up resources
   */
  dispose() {
    this.stopDetection();

    if (this.cameraStream) {
      this.cameraStream.getTracks().forEach(track => track.stop());
      this.cameraStream = null;
    }

    if (this.videoElement) {
      this.videoElement.srcObject = null;
    }

    if (this.model) {
      this.model.dispose();
      this.model = null;
    }

    console.log('[FaceDetection] Resources disposed');
  }
}

// Export for use in index.html
window.FaceDetectionManager = FaceDetectionManager;
