// ==UserScript==
// @name         Midjourney Prompt Submitter & Tracker
// @namespace    http://tampermonkey.net/
// @version      0.3.01
// @description  Auto-fills prompt input, submits it, tracks its progress, and sends status updates back to the server.
// @match        https://www.midjourney.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    console.log("Minerva: Tampermonkey script activated 🥷👾");

    let ws; // Global WebSocket
    const trackedPromptIds = new Set(); // Track which prompt IDs already have an observer

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

    // Function to send status update messages back to the Python server.
    function sendStatus(promptId, status) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            const msg = { prompt_id: promptId, status: status };
            ws.send(JSON.stringify(msg));
            console.log("Minerva: Sent status update:", msg);
        }
    }

    // Polling function to search the container for an element containing the prompt text.
    // When found, it marks that element with a data attribute and attaches an observer.
    function pollPromptProgress(promptId, promptText) {
        // If already tracking this prompt, don't start another poll.
        if (trackedPromptIds.has(promptId)) return;
        const container = document.querySelector('#pageScroll') || document.body;
        console.log("Minerva: Starting to poll progress for prompt:", promptText);
        const pollInterval = setInterval(() => {
            const candidates = Array.from(container.querySelectorAll("*")).filter(node => {
                return node.innerText && node.innerText.toLowerCase().includes(promptText.toLowerCase());
            });
            if (candidates.length > 0) {
                const candidate = candidates[0];
                // Mark the candidate with our prompt id.
                candidate.setAttribute("data-prompt-id", promptId);
                trackedPromptIds.add(promptId);
                // Attach an observer to track progress on this node.
                observeProgress(candidate, promptId, () => {
                    clearInterval(pollInterval);
                });
            }
        }, 1000);
    }

    // Function to attach a MutationObserver to the given node and track progress updates.
    // Calls onComplete when a "100% Complete" / progress_complete status is detected.
    function observeProgress(node, promptId, onComplete) {
        console.log("Minerva: Starting progress tracking for node with promptId:", promptId);
        const observer = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                let txt = "";
                if (mutation.type === "characterData") {
                    txt = mutation.target.data.trim();
                } else if (mutation.type === "childList") {
                    txt = node.innerText.trim();
                }
                if (txt) {
                    const match = txt.match(/(\d+)% Complete/);
                    if (match) {
                        const progress = parseInt(match[1], 10);
                        console.log("Minerva: Progress update for prompt " + promptId + ": " + match[0]);
                        sendStatus(promptId, match[0]); // send progress update
                        if (progress >= 100) {
                            console.log("Minerva: Prompt finished for promptId:", promptId);
                            sendStatus(promptId, "progress_complete");
                            observer.disconnect();
                            if (onComplete) onComplete();
                        }
                    }
                }
            });
        });
        observer.observe(node, { childList: true, subtree: true, characterData: true });
    }

    // Function to simulate submission – uses the React hack to force change detection.
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

        // Simulate Enter key events.
        const keyOptions = { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true };
        inputEl.dispatchEvent(new KeyboardEvent('keydown', keyOptions));
        inputEl.dispatchEvent(new KeyboardEvent('keypress', keyOptions));
        inputEl.dispatchEvent(new KeyboardEvent('keyup', keyOptions));
        console.log("Minerva: Simulated Enter key events dispatched.");

        // Signal that input is complete.
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

        // Start polling for this prompt's progress.
        pollPromptProgress(promptId, promptText);
    }

    // Function to establish (and re-establish) the WebSocket connection.
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
