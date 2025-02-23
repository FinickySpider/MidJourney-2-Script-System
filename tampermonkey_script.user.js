// ==UserScript==
// @name         Midjourney Prompt Submitter & Tracker
// @namespace    http://tampermonkey.net/
// @version      0.3.2
// @description  Auto-fills prompt input, submits it, tracks its progress, and sends status updates back to the server.
// @match        https://www.midjourney.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    console.log("Minerva: Tampermonkey script activated 🥷👾");

    let ws; // Global WebSocket
    const trackedPromptIds = new Set(); // To ensure each prompt is tracked only once

    // Utility: Wait for the target element to be available.
    function waitForElement(selector, callback) {
        const element = document.querySelector(selector);
        if (element) {
            callback(element);
            return;
        }
        const observer = new MutationObserver((mutations, obs) => {
            const el = document.querySelector(selector);
            if (el) {
                obs.disconnect();
                callback(el);
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    // Send status update messages back to the Python server.
    function sendStatus(promptId, status) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            const msg = { prompt_id: promptId, status: status };
            ws.send(JSON.stringify(msg));
            console.log("Minerva: Sent status update:", msg);
        }
    }

    // Polling function that repeatedly searches for a prompt node.
    // If no matching node is found for 60 seconds, assume it's complete.
    function pollPromptProgress(promptId, promptText) {
        // If already tracking, do nothing.
        if (trackedPromptIds.has(promptId)) return;
        trackedPromptIds.add(promptId);
        
        const container = document.querySelector('#pageScroll') || document.body;
        console.log("Minerva: Starting to poll progress for prompt:", promptText);
        let lastUpdateTime = Date.now();
        const pollInterval = setInterval(() => {
            let candidate = null;
            // First, try to find an element with our data attribute.
            const marked = container.querySelector(`[data-prompt-id="${promptId}"]`);
            if (marked) {
                candidate = marked;
            } else {
                // Otherwise, search for an element containing the prompt text.
                const nodes = Array.from(container.querySelectorAll("*")).filter(node => {
                    return node.innerText && node.innerText.toLowerCase().includes(promptText.toLowerCase());
                });
                if (nodes.length > 0) {
                    candidate = nodes[0];
                    candidate.setAttribute("data-prompt-id", promptId);
                }
            }
            if (candidate) {
                const text = candidate.innerText;
                const match = text.match(/(\d+)% Complete/);
                if (match) {
                    const progress = parseInt(match[1], 10);
                    console.log(`Minerva: Polled progress for ${promptId}: ${match[0]}`);
                    sendStatus(promptId, match[0]);
                    lastUpdateTime = Date.now();
                    if (progress >= 100) {
                        console.log("Minerva: Prompt finished for promptId:", promptId);
                        sendStatus(promptId, "progress_complete");
                        clearInterval(pollInterval);
                    }
                }
            } else {
                // If no candidate is found and it's been a while, assume complete.
                if (Date.now() - lastUpdateTime > 60000) { // 60 seconds
                    console.log("Minerva: No prompt element found for 60 seconds; assuming completion for promptId:", promptId);
                    sendStatus(promptId, "progress_complete");
                    clearInterval(pollInterval);
                }
            }
        }, 1000);
    }

    // Simulate submission – using the React hack to force change detection.
    function triggerSubmission(inputEl, promptId, promptText) {
        const lastValue = inputEl.value;
        inputEl.value = promptText;
        if (inputEl._valueTracker) {
            inputEl._valueTracker.setValue(lastValue);
        }
        const inputEvent = new Event('input', { bubbles: true });
        inputEvent.simulated = true;
        inputEl.dispatchEvent(inputEvent);
        const changeEvent = new Event('change', { bubbles: true });
        inputEl.dispatchEvent(changeEvent);
        const keyOptions = { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true };
        inputEl.dispatchEvent(new KeyboardEvent('keydown', keyOptions));
        inputEl.dispatchEvent(new KeyboardEvent('keypress', keyOptions));
        inputEl.dispatchEvent(new KeyboardEvent('keyup', keyOptions));
        console.log("Minerva: Simulated Enter key events dispatched.");
        sendStatus(promptId, "input_complete");
        setTimeout(() => {
            const submitButton = document.querySelector('button[type="submit"], button[class*="submit"]');
            if (submitButton) {
                console.log("Minerva: Found submit button. Clicking it.");
                submitButton.click();
            } else if (inputEl.form) {
                console.log("Minerva: No submit button found; dispatching submit event on form.");
                const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
                inputEl.form.dispatchEvent(submitEvent);
            }
        }, 100);
        pollPromptProgress(promptId, promptText);
    }

    // Establish (and re-establish) the WebSocket connection.
    function connectWebSocket(inputEl) {
        console.log("Minerva: Attempting to connect to WebSocket...");
        ws = new WebSocket("ws://localhost:8080");
        ws.onopen = () => {
            console.log("Minerva: WebSocket connection established.");
        };
        ws.onmessage = (event) => {
            console.log("Minerva: Received prompt:", event.data);
            try {
                const data = JSON.parse(event.data);
                sendStatus(data.prompt_id, "prompt_received");
                inputEl.focus();
                triggerSubmission(inputEl, data.prompt_id, data.text);
            } catch(e) {
                console.error("Minerva: Error parsing prompt JSON:", e);
            }
        };
        ws.onclose = () => {
            console.log("Minerva: WebSocket connection closed. Reconnecting in 3 seconds...");
            setTimeout(() => connectWebSocket(inputEl), 3000);
        };
        ws.onerror = (err) => {
            console.error("Minerva: WebSocket error:", err);
            ws.close();
        };
    }

    waitForElement('#desktop_input_bar', function(inputEl) {
        console.log("Minerva: Input field detected:", inputEl);
        connectWebSocket(inputEl);
    });
})();
