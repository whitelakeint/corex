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
    this._ownsCamera = true;      // false while detecting from the call's stream
    this._savedCallback = null;   // remembered across release/resume
  }

  /**
   * Initialize camera access
   * @returns {Promise<boolean>} Success status
   */
  async initCamera() {
    try {
      console.log('[FaceDetection] Requesting camera access...');

      // Camera only. Presence detection never needs audio, so the kiosk must not
      // hold a microphone while idle — the mic is only acquired by the Tavus call
      // once a conversation actually starts.
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        },
        audio: false
      });

      this.cameraStream = stream;
      this._ownsCamera = true;   // we opened it, so we may stop it

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

      // Load BlazeFace model from a SELF-HOSTED, same-origin copy. The library
      // default fetches from tfhub.dev, which now 302-redirects to a Kaggle
      // signed URL whose signature only covers model.json (not the weights) —
      // so the weight fetch 403s and the browser reports "NetworkError". Serving
      // the model ourselves fixes that and also lets the kiosk run offline.
      const LOCAL_MODEL_URL = '/frontend/models/blazeface/model.json';
      try {
        this.model = await blazeface.load({ modelUrl: LOCAL_MODEL_URL });
      } catch (localErr) {
        console.warn('[FaceDetection] Local model load failed, falling back to default host:', localErr);
        this.model = await blazeface.load();
      }

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
   * Release the camera device so another consumer (the Daily/Tavus call) can
   * use it, WITHOUT tearing down the loaded model. Detection is paused and the
   * current callback is remembered so resumeCamera() can restart cleanly.
   *
   * A single webcam can't be reliably opened by the face detector AND Daily at
   * the same time — leaving it held makes Daily's getUserMedia hang (~30s
   * "enumerateDevices took exceptionally long") and the join times out.
   */
  releaseCamera() {
    this._savedCallback = this.detectionCallback || this._savedCallback || null;
    this.stopDetection();
    // Only stop tracks we actually OWN. During a call the stream belongs to
    // Daily — stopping it would kill the visitor's camera mid-conversation.
    if (this.cameraStream && this._ownsCamera !== false) {
      this.cameraStream.getTracks().forEach(track => track.stop());
    }
    this.cameraStream = null;
    this._ownsCamera = true;
    if (this.videoElement) {
      this.videoElement.srcObject = null;
    }
    console.log('[FaceDetection] Camera released');
  }

  /**
   * Detect from a stream we DON'T own — i.e. Daily's local camera track during
   * an active call. This keeps presence detection running (so "visitor walked
   * away" still ends the session) WITHOUT opening a second getUserMedia on the
   * same device, which is what caused the join contention in the first place.
   * @param {MediaStream} stream - a stream owned by the call
   * @param {string} mode - 'idle' | 'active'
   * @returns {Promise<boolean>} success
   */
  async useExternalStream(stream, mode = 'active') {
    this.releaseCamera();          // drop our own stream if we hold one
    this.cameraStream = stream;
    this._ownsCamera = false;      // the call owns these tracks; never stop them
    if (this.videoElement) {
      this.videoElement.srcObject = stream;
      try {
        await this.videoElement.play();
      } catch (e) {
        console.warn('[FaceDetection] External stream play() failed:', e);
      }
    }
    if (this._savedCallback) {
      this.startDetection(this._savedCallback, mode);
    }
    console.log('[FaceDetection] Detecting from the call camera stream');
    return true;
  }

  /**
   * Re-acquire OUR OWN camera and resume detection with the remembered callback.
   * No-op only if we already hold a live camera of our own — a dead or external
   * (call-owned) stream is discarded and re-opened.
   * @param {string} mode - 'idle' | 'active'
   * @returns {Promise<boolean>} success
   */
  async resumeCamera(mode = 'idle') {
    const holdingLive = this.cameraStream && this._ownsCamera &&
      this.cameraStream.getVideoTracks().some(t => t.readyState === 'live');
    if (holdingLive) return true;

    this.releaseCamera();          // clear a dead or call-owned stream
    const ok = await this.initCamera();
    if (!ok) return false;
    if (this._savedCallback) {
      this.startDetection(this._savedCallback, mode);
    }
    console.log('[FaceDetection] Camera resumed');
    return true;
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
      // BlazeFace's returned object has no top-level dispose(); the disposable
      // tf.GraphModel is nested as `blazeFaceModel`. Guard so cleanup never throws.
      try {
        if (typeof this.model.dispose === 'function') {
          this.model.dispose();
        } else if (this.model.blazeFaceModel && typeof this.model.blazeFaceModel.dispose === 'function') {
          this.model.blazeFaceModel.dispose();
        }
      } catch (e) {
        console.warn('[FaceDetection] Model dispose skipped:', e);
      }
      this.model = null;
    }

    console.log('[FaceDetection] Resources disposed');
  }
}

// Export for use in index.html
window.FaceDetectionManager = FaceDetectionManager;
