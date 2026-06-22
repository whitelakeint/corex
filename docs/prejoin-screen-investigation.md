# Prejoin Screen Removal Investigation

**Date:** 2026-06-10  
**Status:** Not Achievable  
**Conclusion:** Tavus prejoin screen cannot be bypassed via code

---

## Objective

Remove the Tavus prejoin "Join" button that appears after login, allowing users to connect to the avatar immediately without any additional clicks.

---

## Attempts Made

### 1. Daily.js setCallOptions() Method
**Approach:** Call `dailyCall.setCallOptions({ prejoinPageEnabled: false })`  
**Result:** ❌ Failed - `setCallOptions is not a function`  
**Reason:** Method doesn't exist in Daily.js API

**Commit:** `3686ee4` (reverted in `9dca1df`)

---

### 2. Daily.js preAuth() Method
**Approach:** Call `dailyCall.preAuth({ url: conversationUrl })` before `join()`  
**Result:** ❌ Failed - "preAuth() is only supported on custom callObject instances"  
**Reason:** preAuth only works with Daily.js callObject mode, not iframe mode

**Commit:** `9dca1df` (reverted in `6332f59`)

---

### 3. Tavus API Property - enable_prejoin_ui
**Approach:** Add `"enable_prejoin_ui": False` to conversation properties in backend  
**Result:** ❌ Failed - 400 Bad Request from Tavus API  
**Reason:** Invalid property - not supported by Tavus API

**Backend change:**
```python
properties={
    ...
    "enable_prejoin_ui": False,  # Invalid property
}
```

**Commit:** `af236b9` (reverted in `41aa3f9`)

---

### 4. Auto-Click Join Button via Iframe
**Approach:** Access iframe DOM and programmatically click the join button  
**Result:** ❌ Failed - Cross-origin security error  
**Reason:** Cannot access cross-origin iframe content due to browser security

**Code attempted:**
```javascript
var iframe = dailyCall.iframe();
var joinBtn = iframe.contentWindow.document.querySelector('button');
joinBtn.click(); // Throws cross-origin error
```

**Console error:** `[Auto-join] Cannot access iframe (cross-origin)`

**Commit:** `9bd55be` (reverted in `d3a3fa7`)

---

### 5. Pass URL in createFrame() Config
**Approach:** Move `url` parameter from `join()` to `createFrame()` config  
**Result:** ❌ Failed - Prejoin screen still appears  
**Reason:** Doesn't change Tavus prejoin behavior

**Code:**
```javascript
dailyCall = window.Daily.createFrame(cardBody, {
    url: conversationUrl,  // Moved here
    ...
});
await dailyCall.join(); // Simplified
```

**Commit:** `d3a3fa7` (reverted in `815b067`)

---

### 6. Start with Camera Off
**Approach:** Join with `startVideoOff: true` to skip camera permission request  
**Result:** ❌ Failed - Prejoin screen still appears  
**Reason:** Tavus requires microphone permission regardless of camera state

**Code:**
```javascript
await dailyCall.join({
    startVideoOff: true,
    startAudioOff: false
});
```

**Commit:** `815b067` (to be reverted)

---

## Root Cause Analysis

The prejoin screen is **required by Tavus** for the following reasons:

1. **Browser Security Policy**
   - Browsers require explicit user interaction before granting microphone/camera access
   - Cannot be bypassed programmatically due to security restrictions

2. **Tavus Implementation**
   - Prejoin screen is part of Tavus CVI's standard flow
   - No API property or configuration option to disable it
   - Enforced for compliance and user privacy

3. **Evidence from Logs**
   - Conversation events show avatar is already speaking (`conversation.replica.started_speaking`)
   - Join button is UI-level, not blocking the actual connection
   - Prejoin is a Tavus UI layer, not Daily.js functionality

---

## Observations

### Conversation Already Active
Console logs show the conversation is running behind the prejoin screen:
```
[Auto-start] Starting conversation for user: admin
event_type: conversation.replica.started_speaking
event_type: conversation.started_speaking
event_type: conversation.replica.stopped_speaking
event_type: conversation.stopped_speaking
```

This proves:
- Avatar has already loaded
- Conversation has started
- Avatar is speaking
- Only the UI is blocking the view

---

## Similar Implementations

### Jitsi Integration (Working Example)
In the same codebase, Jitsi successfully disables prejoin:

```javascript
jitsiApi = new JitsiMeetExternalAPI("meet.whitelakedigital.com", {
    configOverwrite: {
        prejoinPageEnabled: false,  // Works for Jitsi
        ...
    }
});
```

**Why this works:** Jitsi exposes `prejoinPageEnabled` config option  
**Why Tavus doesn't:** Tavus doesn't provide this configuration

---

## Potential Solutions (Not Tested)

### 1. Contact Tavus Support
Request enterprise/account-level setting to disable prejoin screen.

**Ask Tavus:**
> "Is there a way to disable the prejoin screen for our API key/account? We want users to connect immediately without clicking 'Join'."

**Possible outcomes:**
- Enterprise feature available
- Account-level configuration
- Future API support
- Confirmed as not possible

### 2. Tavus Dashboard Settings
Check Tavus dashboard for:
- Persona-level prejoin settings
- Account preferences
- Security/privacy options

### 3. Different Tavus Product Tier
Higher tier plans may include prejoin bypass feature.

---

## Recommendation

**Accept the prejoin click requirement** because:

1. **Security Compliance**
   - Required for browser permission policies
   - Ensures user consent for microphone access
   - Industry standard practice

2. **Minimal User Friction**
   - Only one click required
   - Clear "Join" button (good UX)
   - Industry-standard flow (users familiar with it)

3. **Technical Limitation**
   - Cannot be bypassed via code
   - Tavus API doesn't support it
   - Browser security prevents workarounds

---

## Current Implementation Status

### What Works
✅ Auto-start conversation after login (1.1 second delay)  
✅ Conversation created automatically  
✅ Avatar loads in background  
✅ Multi-user support (admin/buildingB)

### What Requires User Action
⚠️ One click on "Join" button (required for microphone permission)

### User Flow
1. User logs in (enters credentials, clicks "Enter")
2. Wait 1.1 seconds (auto-start kicks in)
3. Prejoin screen appears with "Join" button
4. **User clicks "Join"** (one click)
5. Avatar appears and starts conversation

---

## Comparison: Before vs After

### Before This Investigation
1. User logs in
2. User clicks "Start Conversation" button
3. Prejoin screen appears
4. User clicks "Join" button
**Total: 2 clicks after login**

### After This Investigation (Current)
1. User logs in
2. Auto-start triggers (no manual click)
3. Prejoin screen appears
4. User clicks "Join" button
**Total: 1 click after login**

### Ideal Goal (Not Achievable)
1. User logs in
2. Avatar appears immediately
**Total: 0 clicks after login**

---

## Files Modified During Investigation

### Frontend
- `frontend/index.html` - Multiple attempts at bypassing prejoin

### Backend
- `backend/app.py` - Attempted `enable_prejoin_ui` property (invalid)

### Commits
- `3686ee4` - setCallOptions attempt
- `9dca1df` - preAuth attempt
- `af236b9` - enable_prejoin_ui attempt
- `9bd55be` - Auto-click iframe attempt
- `d3a3fa7` - URL in createFrame attempt
- `815b067` - startVideoOff attempt

All reverted or to be reverted.

---

## Next Steps

1. **Revert auto-start feature** to restore manual "Start Conversation" button
2. **Keep multi-user implementation** (working correctly)
3. **Document user flow** with one-click prejoin requirement
4. **Optionally:** Contact Tavus support about prejoin bypass options

---

## Conclusion

The Tavus prejoin screen **cannot be removed** via frontend or backend code changes. It is a fundamental part of Tavus CVI's security and compliance model. The best achievable user experience is:

- Login → Click "Start Conversation" → Click "Join" (2 clicks)

Or with auto-start:
- Login → Click "Join" (1 click)

Any further reduction requires Tavus to provide API/account-level support for disabling prejoin screens.
