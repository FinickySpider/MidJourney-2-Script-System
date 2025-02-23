// ==UserScript==
// @name         Midjourney Prompt Submitter & Tracker
// @namespace    http://tampermonkey.net/
// @version      0.3
// @description  Auto-fills prompt input, submits it, tracks progress, and sends status updates back to the server.
// @match        https://www.midjourney.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    console.log("Minerva: Tampermonkey script activated 🥷👾");

    let ws; // Global WebSocket

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

    function sendStatus(promptId, status) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            const msg = { prompt_id: promptId, status: status };
            ws.send(JSON.stringify(msg));
            console.log("Minerva: Sent status update:", msg);
        }
    }

    function pollPromptProgress(promptId, promptText) {
        const container = document.querySelector('#pageScroll') || document.body;
        console.log("Minerva: Starting to poll progress for prompt:", promptText);
        const intervalId = setInterval(() => {
            const nodes = container.querySelectorAll("*");
            nodes.forEach(node => {
                if (node.innerText && node.innerText.toLowerCase().includes(promptText.toLowerCase())) {
                    const match = node.innerText.match(/(\d+)% Complete/);
                    if (match) {
                        const progress = parseInt(match[1], 10);
                        console.log("Minerva: Polled progress update:", match[0]);
                        sendStatus(promptId, match[0]);
                        if (progress >= 100) {
                            console.log("Minerva: Prompt finished (polled):", node);
                            sendStatus(promptId, "progress_complete");
                            clearInterval(intervalId);
                        }
                    }
                }
            });
        }, 1000);
    }

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
