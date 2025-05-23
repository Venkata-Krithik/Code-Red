# Code-Red
Dynamic Master Election in IoT Sensor Network
---

##  Overview

**Goal:**  
Build a compact, affordable emergency detection and response system using IoT components that can operate autonomously or with minimal intervention.

**Core Idea:**
- **Raspberry Pi** acts as a local coordinator or listener.
- **ESP8266-based Node (Arduino IDE)** detects danger events and broadcasts signals.
- Visual feedback (LEDs) and alerts are triggered when a condition is met.
- Optionally displays information on a web interface.

---

##  Components Used

- 🔌 **Raspberry Pi**
- 📶 **ESP8266 Wi-Fi Module**
- 💡 **LEDs for visual alert**
- 👇 **Push Button for user interaction**
- 🌐 **Web Interface (HTML)**
![image](https://github.com/user-attachments/assets/23064430-14d1-47af-84a1-f128f98da3ab)


---

##  Communication Flow

1. **ESP8266 Node**
   - Collects input (e.g., button press or sensor).
   - Sends UDP or HTTP-based messages to Raspberry Pi.

2. **Raspberry Pi**
   - Listens for broadcast signals.
   - Activates corresponding LEDs.
   - Logs event or serves updated webpage.

3. **Web Interface**
   - Displays system status or alert condition.
   ![image](https://github.com/user-attachments/assets/6ec2e10d-a4e1-4608-bf97-7704cbec0539)

   ![image](https://github.com/user-attachments/assets/f3617a42-c5d8-47d9-a2a7-3c29bed3b0f6)


   ![image](https://github.com/user-attachments/assets/96296505-c390-456f-979e-91d3196d25d2)


---

##  File Descriptions

- `IoTCodeRed.ino`:  
  Arduino sketch for the ESP8266. Handles button state reading and broadcasting alert messages.

- `Pi code.py`:  
  Python script for Raspberry Pi. Listens for incoming messages and responds by toggling LEDs or logging data.

- `iotFinalWorking.html`:  
  Basic HTML interface for visualization or status dashboard.

- `Code_Red_Final.pdf`:  
  Detailed report documenting design, circuit diagrams, use cases, and testing.

---

## 🚀 Getting Started

### Raspberry Pi Setup

```bash
# Install required Python libraries
pip install socket
python3 "Pi code.py"
