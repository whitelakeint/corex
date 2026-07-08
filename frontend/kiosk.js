/* =============================================================================
 * kiosk.js — presence-gated kiosk client.
 *
 * Fetches /api/config to decide how the portal runs:
 *   - skip_login : reveal the app immediately (no username/password gate)
 *   - kiosk_mode : full presence-gated kiosk. A local WebSocket to the presence
 *                  controller drives which layer is shown:
 *                    attract      -> loop the cheap local video (no Tavus room)
 *                    greeting     -> short bridge clip while the room spins up
 *                    conversation -> join the live Tavus room (window.ConciergeApp)
 *
 * The controller owns the conversation lifecycle; this file only swaps layers
 * and reports room_joined / room_ended back over the socket.
 * ========================================================================== */
(function () {
  "use strict";

  var RECONNECT_MS = 2000;

  var loginScreen = document.getElementById("login-screen");
  var appScreen = document.getElementById("app-screen");
  var attractLayer = document.getElementById("kiosk-attract");
  var greetingLayer = document.getElementById("kiosk-greeting");
  var attractVideo = document.getElementById("kiosk-attract-video");
  var greetingVideo = document.getElementById("kiosk-greeting-video");

  var ws = null;
  var wsUrl = null;
  var currentCmd = null;   // last command applied ("attract"|"greeting"|"conversation")
  var currentUrl = null;   // url of the room currently open

  function revealApp() {
    if (loginScreen) loginScreen.style.display = "none";
    if (appScreen) appScreen.classList.add("visible");
  }

  function showLayer(layer) {
    [attractLayer, greetingLayer].forEach(function (el) {
      if (el) el.classList.remove("visible");
    });
    if (layer) layer.classList.add("visible");
  }

  function sendEvent(event) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      try { ws.send(JSON.stringify({ event: event })); } catch (e) {}
    }
  }

  /* ---- command handlers ---------------------------------------------- */
  function cmdAttract() {
    showLayer(attractLayer);
    if (attractVideo) { try { attractVideo.play(); } catch (e) {} }
    // If a room was open, tear it down (controller already ended billing).
    if (currentCmd === "conversation" && window.ConciergeApp) {
      window.ConciergeApp.closeRoom();
    }
    currentUrl = null;
  }

  function cmdGreeting() {
    showLayer(greetingLayer);
    if (greetingVideo) {
      try { greetingVideo.currentTime = 0; greetingVideo.play(); } catch (e) {}
    }
  }

  function cmdConversation(url) {
    if (!url) return;
    if (currentCmd === "conversation" && currentUrl === url) return;  // already joined
    currentUrl = url;
    if (!window.ConciergeApp) {
      console.error("[kiosk] ConciergeApp bridge missing");
      return;
    }
    window.ConciergeApp.openRoom(url)
      .then(function () {
        showLayer(null);        // hide overlays -> live room visible underneath
        sendEvent("room_joined");
      })
      .catch(function (err) {
        console.error("[kiosk] Failed to open room:", err);
        // Fall back to attract so we never get stuck on a black screen.
        cmdAttract();
      });
  }

  function applyCommand(msg) {
    var cmd = msg && msg.cmd;
    if (!cmd) return;
    console.log("[kiosk] command:", cmd);
    if (cmd === "attract") cmdAttract();
    else if (cmd === "greeting") cmdGreeting();
    else if (cmd === "conversation") cmdConversation(msg.url);
    else { console.warn("[kiosk] unknown command:", cmd); return; }
    currentCmd = cmd;
  }

  /* ---- websocket with auto-reconnect --------------------------------- */
  function connect() {
    console.log("[kiosk] connecting to", wsUrl);
    try {
      ws = new WebSocket(wsUrl);
    } catch (e) {
      console.error("[kiosk] ws construct failed:", e);
      scheduleReconnect();
      return;
    }

    ws.onopen = function () { console.log("[kiosk] ws connected"); };

    ws.onmessage = function (event) {
      var msg;
      try { msg = JSON.parse(event.data); }
      catch (e) { console.warn("[kiosk] bad ws message:", event.data); return; }
      applyCommand(msg);
    };

    ws.onclose = function () {
      console.warn("[kiosk] ws closed; reconnecting");
      scheduleReconnect();
    };

    ws.onerror = function () {
      // onclose will follow and trigger the reconnect.
      try { ws.close(); } catch (e) {}
    };
  }

  function scheduleReconnect() {
    setTimeout(connect, RECONNECT_MS);
  }

  /* ---- bootstrap ----------------------------------------------------- */
  fetch("/api/config")
    .then(function (r) { return r.json(); })
    .then(function (cfg) {
      cfg = cfg || {};

      // Property label on the attract fallback + document title.
      if (cfg.property_name) {
        var t = document.getElementById("kiosk-attract-title");
        if (t) t.textContent = cfg.property_name;
      }

      if (cfg.skip_login && !cfg.kiosk_mode) {
        // Env-configured property, no login gate, but still manual Start.
        revealApp();
        return;
      }

      if (!cfg.kiosk_mode) return;  // ordinary manual portal — leave as-is

      // --- full kiosk mode ---
      document.body.classList.add("kiosk");
      revealApp();
      showLayer(attractLayer);
      currentCmd = "attract";

      // Report client-side room end (e.g. hangup) to the controller.
      window.ConciergeApp.onRoomEnded = function () {
        console.log("[kiosk] room ended (client side)");
        sendEvent("room_ended");
        cmdAttract();
        currentCmd = "attract";
      };

      wsUrl = cfg.ws_url || "ws://127.0.0.1:8765";
      connect();
    })
    .catch(function (err) {
      console.error("[kiosk] /api/config failed:", err);
    });
})();
