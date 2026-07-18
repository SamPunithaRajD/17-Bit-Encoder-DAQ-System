# 17-Bit Absolute Encoder Data Acquisition System

An industrial-grade real-time Data Acquisition (DAQ) system developed for the **Indian Institute of Astrophysics (IIA)**, **Vainu Bappu Observatory (VBO), Kavalur**.

This application is designed to communicate with a physical **ICP DAS PIO-D144 PCI Digital I/O Card** through the official UniDAQ Driver SDK to continuously acquire the 17-bit parallel output of a **Gurley A25S Absolute Rotary Encoder** mounted on the observatory dome.

---

## 🎓 Internship & Credits
* **Observatory Venue**: Vainu Bappu Observatory (VBO), Kavalur — Indian Institute of Astrophysics (IIA)
* **Industry Mentor**: Mrs. Vellai Selvi, Engineer D, VBO
* **Developer**: Sam Punitha Raj D (Intern)
* **Institution**: St. Joseph's College of Engineering
* **Department**: Computer Science and Engineering

---

## 🛠️ Hardware Specifications & Architecture
* **Interface Card**: ICP DAS PIO-D144 / PIO-D144U Universal PCI Digital I/O Card (144 channels, TTL compatible).
* **Sensor**: Gurley A25S 17-Bit Absolute Rotary Encoder ($2^{17} = 131,072$ positions).
* **Communication Code**: Parallel Natural Binary (default factory configuration of the Gurley A25S).
* **Physical Connectors**: Supported across six mapping configurations (CN1–CN6 on the PIO-D144 board) using 50-pin flat ribbon ribbon cables.

---

## 🚀 Key Technical Features

### 1. Two-Phase Hardware Verification Sequence
Safely splits the initialization path to prevent system faults:
* **Phase 1 (PCI Board Verification)**: Verifies `UniDAQ.dll` loading, driver state, board registry info (Model, Card ID, PCI Bus, Slot, IRQ), and executes a physical test read. If the card is missing, initialization halts safely, lighting the Driver/Card status indicators **RED**.
* **Phase 2 (Encoder Connector Scan)**: Initiated only if Phase 1 passes. Scans Connectors 1–6 (or uses manual settings) to check for stable, valid encoder signals.

### 2. Robust Connector Stability Filter
Floating open-circuits are rejected by filtering out default static lines ($0$ and $131,072$). High-frequency EMI noise from local dome motors is rejected using a 10-sample sliding-window checks with $5\text{ms}$ delays, ensuring a stable tracking delta ($\Delta < 500$ counts) before locking the active connector.

### 3. Wrap-Around & Direction Tracking
Utilizes circle modulo arithmetic to handle transitions across the $359.999^\circ \leftrightarrow 0.000^\circ$ physical gap, providing smooth tracking deltas:
$$\Delta = \left( (\text{curr\_count} - \text{prev\_count} + \text{half}) \bmod \text{total} \right) - \text{half}$$

### 4. Real-Time Diagnostics Panel
The dark-themed GUI displays:
* **Subsystem Indicators**: Separate, isolated status LEDs (Driver, Card, Encoder, Acquisition).
* **Telemetry**: Decimal count, binary representation, hexadecimal, degrees, and Degrees-Minutes-Seconds (DMS) string representation.
* **Diagnostics**: Individual raw port bytes, read cycle frequency (Hz), active connector indices, and hardware PCI addresses.

### 5. Memory-Safe Event Logger
A circular buffer is enforced on the event log text control, restricting it to 1000 lines to prevent memory footprint growth during weeks of unattended, continuous runs.

---

## 📂 Project Directory Structure
```text
├── encoder_daq_single.py  # Unified, production-grade application script
├── config.ini             # System parameters and calibration configurations
├── UniDAQ.dll             # Driver SDK library mapping the PCI slot interface
├── .gitignore             # Ignores compiled caches and local execution logs
└── README.md              # Documentation
```

---

## 💻 Prerequisites & Setup

### **1. Hardware Setup**
* Ensure the ICP DAS PIO-D144 Universal PCI Card is securely seated in a PCI slot on the motherboard.
* Verify the UniDAQ Windows driver package is installed.

### **2. Software Setup**
1. Copy `UniDAQ.dll` and `config.ini` into the same directory as `encoder_daq_single.py`.
2. Install Python 3.8+ (x86 or x64 matching your DLL architecture).
3. Install the required GUI library dependencies:
   ```bash
   pip install wxPython
   ```

### **3. Running the Application**
Run the unified script directly using Python:
```bash
python encoder_daq_single.py
```
* **Auto Mode**: The application will automatically scan connectors 1 to 6 on startup to detect the encoder.
* **Manual Mode**: Select a fixed connector (Connector 1–6) in the Preferences dialog to skip scanning and configure it immediately.
