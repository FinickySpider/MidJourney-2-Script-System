// ==UserScript==
// @name         Midjourney Prompt Submitter
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Auto-fills prompt input and submits on midjourney.com/imagine/ via WebSocket input 🧑‍💻🔓
// @match        https://www.midjourney.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    console.log("Minerva: Tampermonkey script activated 🥷👾");

    // Utility: Wait for the target element to be available
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

    // Function to simulate submission – try both Enter key events and a form/button submission.
    function triggerSubmission(inputEl, promptText) {
        // Use the React hack to force change detection
        const lastValue = inputEl.value;
        inputEl.value = promptText;
        if (inputEl._valueTracker) {
            inputEl._valueTracker.setValue(lastValue);
        }
        // Dispatch a native input event
        const inputEvent = new Event('input', { bubbles: true });
        inputEvent.simulated = true;
        inputEl.dispatchEvent(inputEvent);

        // Dispatch change event as well
        const changeEvent = new Event('change', { bubbles: true });
        inputEl.dispatchEvent(changeEvent);

        // Simulate Enter key press with keydown, keypress, then keyup
        const keyOptions = { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true };
        inputEl.dispatchEvent(new KeyboardEvent('keydown', keyOptions));
        inputEl.dispatchEvent(new KeyboardEvent('keypress', keyOptions));
        inputEl.dispatchEvent(new KeyboardEvent('keyup', keyOptions));
        console.log("Minerva: Simulated Enter key events dispatched.");

        // As an additional fallback, attempt to submit via button click or form submit
        setTimeout(() => {
            // Try to find a submit button (if one exists)
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
    }

    // Function to establish (and re-establish) the WebSocket connection
    function connectWebSocket(inputEl) {
        console.log("Minerva: Attempting to connect to WebSocket...");
        const ws = new WebSocket("ws://localhost:8080");
        ws.onopen = () => {
            console.log("Minerva: WebSocket connection established.");
        };
        ws.onmessage = (event) => {
            console.log("Minerva: Received prompt:", event.data);
            // Ensure the input field is focused
            inputEl.focus();
            // Trigger the submission sequence
            triggerSubmission(inputEl, event.data);
        };
        ws.onclose = () => {
            console.log("Minerva: WebSocket connection closed. Reconnecting in 3 seconds...");
            setTimeout(() => connectWebSocket(inputEl), 3000);
        };
        ws.onerror = (err) => {
            console.error("Minerva: WebSocket error:", err);
            ws.close(); // Trigger onclose to re-establish connection
        };
    }

    // Wait for the Midjourney prompt input field (#desktop_input_bar)
    waitForElement('#desktop_input_bar', function(inputEl) {
        console.log("Minerva: Input field detected:", inputEl);
        connectWebSocket(inputEl);
    });
})();
