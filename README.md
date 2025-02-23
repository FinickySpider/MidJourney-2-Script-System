# MJ-Control & MJ-Agent  

**MJ-Control & MJ-Agent** is a two-part system designed to **automate prompt submission** on MidJourney.  
- **MJ-Control** 🖥️ → The **desktop application** that manages automation settings, prompt generation, and server communication.  
- **MJ-Agent** 🤖 → The **browser userscript** that inputs, submits, and tracks MidJourney prompts.  

MJ-Control generates dynamic prompts (with advanced wildcard expansion & concurrency control) and communicates with MJ-Agent via **WebSockets** to track prompt progress in real-time.  

---

## 📜 Table of Contents  

- [Features](#features)  
- [Overview](#overview)  
- [Setup Instructions](#setup-instructions)  
  - [MJ-Control Setup (Windows)](#mj-control-setup-windows)  
  - [MJ-Agent Setup (Tampermonkey Userscript)](#mj-agent-setup-tampermonkey-userscript)  
- [Usage](#usage)  
- [Advanced Wildcards](#advanced-wildcards)  
- [Known Issues](#known-issues)  
- [Changelog](#changelog)  
- [License](#license)  

---

## 🔥 Features  

✅ **Automated Prompt Generation** – MJ-Control generates prompts dynamically, supports **nested wildcards**, and ensures unique ID tracking.  
✅ **Bidirectional WebSocket Communication** – Real-time status updates between **MJ-Control** & **MJ-Agent**.  
✅ **Concurrency Control** – Limits active prompts to prevent API overload.  
✅ **Progress Tracking** – MJ-Agent polls MidJourney’s UI to **monitor completion percentages**.  
✅ **Configurable UI (Windows Only)** – MJ-Control features a **Tkinter-based UI** for managing automation settings.  
✅ **Standalone EXE Support** – MJ-Control can be compiled into a **Windows executable** using PyInstaller.  

---

## 🛠️ Overview  

This system consists of **two components:**  

### 🖥️ **MJ-Control (Desktop Application)**
- Generates and sends prompts via **WebSockets**.
- Controls **concurrent submissions** & ensures automation safety.
- Provides a **GUI** for easy configuration.
- Tracks **prompt progress** via WebSocket feedback.

### 🤖 **MJ-Agent (Userscript for Tampermonkey)**
- Runs on **MidJourney’s website** inside your browser.
- Listens for incoming prompts from MJ-Control.
- Inputs, submits, and tracks each prompt’s progress.
- Sends **real-time status updates** back to MJ-Control.

---

## 📥 Setup Instructions  

### 🔹 **MJ-Control Setup (Windows)**
#### **1️⃣ Install Prerequisites**
- Install **Python 3.11+**  
- Install **dependencies**:  
  ```bash
  pip install websockets pyinstaller
  ```
  
#### **2️⃣ Clone & Configure**
```bash
git clone https://github.com/FinickySpider/MJ-Control.git
cd MJ-Control
```
- Edit **`config.ini`** (or let MJ-Control create one).  

#### **3️⃣ Run MJ-Control**
```bash
python mj_control.py
```
_(or compile it into an `.exe`)_

#### **4️⃣ Compile to EXE (Optional)**
```bash
pyinstaller --onefile --windowed --icon=Icon.ico --clean mj_control.py
```
_(Executable will be in the `dist/` folder)_

---

### 🔹 **MJ-Agent Setup (Tampermonkey Userscript)**  

#### **1️⃣ Install Tampermonkey**
- [Download Tampermonkey](https://www.tampermonkey.net/) for your browser.

#### **2️⃣ Install MJ-Agent**
- **[Click here to install MJ-Agent](https://finickyspider.github.io/MidJourney-2-Script-System/tampermonkey_script.user.js)**  
  _or manually paste the script into Tampermonkey._

#### **3️⃣ Start MidJourney Automation**
- Open **MidJourney’s website**.  
- MJ-Agent will **automatically detect & submit prompts** from MJ-Control.

---

## ▶️ Usage  

### **1️⃣ Start MJ-Control**
Run `mj_control.py` or `MJ-Control_v0.2-pre1.exe`.

### **2️⃣ Start the Automation**
Click **"Start Server"** in the GUI. It will begin sending prompts when active.

### **3️⃣ Monitor Progress**
- MJ-Control logs **prompt IDs** and progress updates.  
- MJ-Agent **tracks prompt completion** & updates MJ-Control.  

---

## 🎯 Advanced Wildcards  

**MJ-Control** supports **recursive wildcard expansion** for random, dynamic prompt generation.

#### **📜 Example Wildcard Setup**
```ini
[Settings]
PromptTemplate = "a [STYLE] [SUBJECT]"
```
```
wildcards/
├── STYLE.txt
│   ├── cyberpunk
│   ├── steampunk
│   ├── neon glow
├── SUBJECT.txt
│   ├── warrior
│   ├── robot
│   ├── samurai
```
🔥 **Possible Output:**  
✅ `"a cyberpunk warrior"`  
✅ `"a neon glow robot"`  

---

## 🛠️ Known Issues  

### **🚨 WebSocket Connection Issues**  
- Ensure **MJ-Control is running before launching MidJourney.**  
- **Firewall issues?** Allow Python through Windows Defender.

### **🖥️ Windows-Only GUI**  
- The **Tkinter-based UI is not fully supported on Mac/Linux** _(CLI mode works)._

### **⏳ Prompt Node Tracking**  
- MJ-Agent **monitors page updates**, but dynamic MidJourney UI changes may require script adjustments.

---

## 📌 Changelog  

### **v0.2-pre1**
- First pre-release of **MJ-Control (Desktop App Only).**
- **MJ-Agent is available separately.**  

### **v0.1**
- Initial automation system with WebSocket communication.  

---

## 📜 License  
This project is licensed under the [MIT License](LICENSE).

---

## 📬 Contact  
For questions or support, open an issue on GitHub or contact **[finickyspider@gmail.com](mailto:finickyspider@gmail.com).**  