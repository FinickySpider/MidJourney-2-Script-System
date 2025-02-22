# Midjourney Automation Utility

**Midjourney Automation Utility** is a two-script system designed to automate prompt submission on Midjourney. It consists of a Python automation script that generates dynamic prompts (with advanced wildcard expansion and concurrency control) and a Tampermonkey userscript that runs in your browser on Midjourney to input, submit, and track the progress of each prompt. Status updates are sent back to the Python script so you can monitor each prompt’s life cycle.

---

## Table of Contents

- [Features](#features)
- [Overview](#overview)
- [Setup Instructions](#setup-instructions)
  - [Prerequisites](#prerequisites)
  - [Python Script Setup (Windows)](#python-script-setup-windows)
  - [Tampermonkey Userscript Setup](#tampermonkey-userscript-setup)
- [Usage](#usage)
- [Wildcards & Advanced Examples](#wildcards--advanced-examples)
- [Known Issues & Bugs](#known-issues--bugs)
- [Changelog](#changelog)
- [License](#license)

---

## Features

- **Automated Prompt Generation:**  
  The Python script generates prompts based on a configurable template. It supports nested wildcard expansion (even with symbols like `-`, underscores, digits, or other characters) and can generate unique prompts with unique IDs.

- **Concurrency Control:**  
  Set a maximum number of concurrent prompts. The server waits until the number of in-flight prompts is below the configured maximum before sending new ones.

- **Bidirectional WebSocket Communication:**  
  The Python server sends prompts (with unique IDs) as JSON messages to the userscript. The userscript simulates input and submission on the Midjourney page and sends back status updates ("prompt_received", "input_complete", progress updates, and "progress_complete") so that the server can track the progress of each prompt.

- **Progress Tracking:**  
  The userscript polls the page for nodes containing the submitted prompt text and logs progress updates (e.g., “10% Complete”, “100% Complete”), ensuring that even if the node moves due to dynamic page updates, progress is still tracked.

- **UI & Configuration:**  
  A Tkinter-based UI (currently for Windows) allows you to toggle the server ON/OFF, view server status, and configure settings such as `PromptTemplate`, `MessageSendDelay`, and `MaxConcurrentPrompts`. Changes are saved to the config file and take effect immediately.

- **Easy Compilation:**  
  The Python script can be compiled into a standalone executable using PyInstaller, so you can run it on Windows without needing to install Python separately.

---

## Overview

This project automates prompt submissions on Midjourney with real-time prompt tracking. The two main components are:

1. **Python Automation Script:**  
   - Generates prompts using a customizable template.
   - Supports advanced wildcard expansion with nested wildcards.
   - Controls the rate and maximum number of concurrent prompts.
   - Runs a WebSocket server to communicate with the userscript.
   - Provides a GUI to modify configuration parameters.
   - Tracks prompt statuses based on client feedback.

2. **Tampermonkey Userscript:**  
   - Runs on [Midjourney](https://www.midjourney.com/imagine/) and waits for the prompt input field.
   - Receives JSON messages (with prompt text and unique IDs) from the Python server.
   - Automatically fills in the prompt, simulates the Enter key to submit, and tracks progress.
   - Sends status updates back to the Python server via WebSocket.

---

## Setup Instructions

### Prerequisites

- **Python 3.11+** (tested on Windows)
- **Tkinter:** Included with standard Python installations on Windows.
- **Websockets Library:** Install via pip  
  ```bash
  pip install websockets
  ```
- **PyInstaller:** For compiling the Python script into an executable  
  ```bash
  pip install pyinstaller
  ```
- **Tampermonkey:** Install the Tampermonkey extension for your browser (Chrome, Edge, etc.)

---

### Python Script Setup (Windows)

1. **Clone or Download the Repository:**

   ```bash
   git clone https://github.com/FinickySpider/MidJourney-2-Script-System.git
   cd MidJourney-2-Script-System
   ```

2. **Edit the Configuration File:**  
   Open `config.ini` (if not present, create it or let the script auto-create it) and set your initial values:
   
   ```ini
   [Settings]
   PromptTemplate = a [STYLE] [TYPE] character
   MessageSendDelay = 5
   MaxConcurrentPrompts = 3
   WildcardDirectory = wildcards
   RecursionDepth = 5
   ```

3. **Run the Python Script:**  
   Simply run:
   ```bash
   python midjourney_automation.py
   ```
   A Tkinter window will appear that lets you turn the server on/off and change configuration values.

4. **Compile to EXE (Optional):**  
   Once you’ve verified that the script works as expected, compile it:
   ```bash
   pyinstaller --onefile midjourney_automation.py
   ```
   The executable will be found in the `dist` folder.

---

### Tampermonkey Userscript Setup

1. **Install Tampermonkey:**  
   Install Tampermonkey for your preferred browser from [tampermonkey.net](https://www.tampermonkey.net/).

2. **Add the Userscript:**

   - Follow this [link](https://finickyspider.github.io/MidJourney-2-Script-System/tampermonkey_script.user.js) to install the script automatically.

   OR

   - Open the Tampermonkey dashboard.
   - Click “Create a new script.”
   - Replace the template with the content from `Midjourney_Prompt_Submitter_Tracker.user.js` (see below).
   - Save the script.

3. **Visit Midjourney:**  
   Navigate to [https://www.midjourney.com](https://www.midjourney.com). The script will wait for the prompt input field, connect to the Python server, and process prompts.

---

## Usage

1. **Start the Python Script:**  
   Run `midjourney_automation.py` (or the compiled EXE). The UI window should open.

2. **Turn the Server ON:**  
   Click the **ON** button. The status indicator will change to “Server ON.”

3. **Configure Settings (Optional):**  
   Change the prompt template, message delay, or max concurrent prompts in the UI and click **Save Config**.  
   - **Prompt Template Example:**  
     `a [WILDS] [WILDS] character`  
     where `WILDS.txt` might include lines that themselves include nested wildcards (e.g., `[technology_mecha]`, `[posture_leg_location]`, etc.)
   
4. **Install the Tampermonkey Script:**  
   Ensure the Tampermonkey script is active in your browser.
   
5. **Triggering and Tracking Prompts:**  
   When the Python script sends a prompt, the userscript receives it, submits it, and starts tracking progress. It sends status updates back to the Python script, which logs the prompt’s progress until it reaches 100%.

---

## Wildcards & Advanced Examples

Wildcards are defined in text files inside the `wildcards/` directory. Each file is named with the wildcard key (e.g., `WILDS.txt`, `STYLE.txt`, `TYPE.txt`), and the keys are normalized to uppercase for lookup.

- **Basic Example:**  
  - **Prompt Template:**  
    `a [STYLE] [TYPE] character`
  - **STYLE.txt:**  
    ```
    cyberpunk
    fantasy
    [LIGHTING] steampunk
    ```
  - **TYPE.txt:**  
    ```
    ninja
    robot
    cat
    ```
  - **LIGHTING.txt:**  
    ```
    neon
    soft glow
    ```
  - **Result:**  
    Possible expansion: `a cyberpunk ninja character` or `a neon steampunk robot character`

- **Advanced Wildcard Example:**  
  - **Prompt Template:**  
    `a [WILDS] [WILDS] character`
  - **WILDS.txt:**  
    ```
    [technology_mecha] Printcore
    EMC Corporation [posture_leg_location]
    abstract
    vivid
    ```
  - **technology_mecha.txt:**  
    ```
    mecha
    robotic
    cybernetic
    ```
  - **posture_leg_location.txt:**  
    ```
    standing
    crouching
    leaping
    ```
  - **Result:**  
    Possible expansion: `a mecha Printcore character` or `a EMC Corporation crouching character`
  
*Note:* The regex in the Python script now accepts any symbol allowed in a file name (including dashes, underscores, digits, etc.) between the square brackets, so the wildcards work regardless of case or punctuation.

---

## Known Issues & Bugs

- **Prompt Node Tracking:**  
  In highly dynamic pages, prompt nodes might be re-rendered or moved. The polling mechanism in the userscript should mitigate this, but there may be edge cases where progress is not detected.
  
- **WebSocket Connection:**  
  The system currently only supports one active client (or a small number) on Windows. Linux and macOS support is forthcoming.
  
- **Status Updates:**  
  If multiple prompts are sent rapidly, there might be overlapping status messages. The Python server tracks prompt statuses individually by their unique IDs; ensure that the prompt template and wildcard expansions are configured to avoid duplicate prompt texts if unique tracking is desired.

- **Limited OS Support:**  
  Currently, the Python script (especially the Tkinter UI) is tested only on Windows. Linux and macOS compatibility is planned for future updates.

---

## Changelog

### v0.2
- Added polling in the Tampermonkey userscript to continuously track progress even if prompt nodes are moved.
- Modified the userscript to send status updates (“prompt_received”, “input_complete”, progress updates, “progress_complete”) back to the Python server.

### v0.1
- Initial release with Python automation script that generates prompts with wildcard expansion.
- Integrated a basic Tkinter UI for configuration (PromptTemplate, MessageSendDelay, MaxConcurrentPrompts).
- Implemented WebSocket communication between Python and the Tampermonkey userscript.
- Added prompt tracking and concurrency control on the Python side.
- Userscript simulates input and submission on Midjourney and tracks progress of submitted prompts.

---

## License

This project is licensed under the [MIT License](LICENSE). [IDK YET PLACEHOLDERR]

---

## Contributing

Contributions, bug reports, and feature requests are welcome! Please open an issue or submit a pull request on GitHub.

---

## Contact

For any questions or support, please open an issue in the GitHub repository or contact the maintainer at [finickyspider@gmail.com](mailto:finickyspider@gmail.com).

