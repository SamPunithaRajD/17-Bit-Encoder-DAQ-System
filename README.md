 <div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&height=250&color=0:020617,30:0B2545,65:075985,100:06B6D4&text=17-BIT%20ENCODER&fontSize=58&fontColor=FFFFFF&fontAlignY=37&desc=REAL-TIME%20DATA%20ACQUISITION%20SYSTEM&descSize=17&descAlignY=58&animation=fadeIn&stroke=22D3EE&strokeWidth=1" width="100%" alt="17-bit Encoder Data Acquisition System"/>

<img src="https://readme-typing-svg.demolab.com?font=Orbitron&weight=600&size=18&duration=2400&pause=650&color=22D3EE&center=true&vCenter=true&width=850&lines=ACQUIRE.+PROCESS.+MONITOR.;ENGINEERING+MEETS+SCIENTIFIC+INSTRUMENTATION.;REAL-TIME+DATA.+PRECISION.+RELIABILITY.;BUILT+WITH+PYTHON." alt="Animated project tagline"/>

<br/>

**A Python-powered desktop application for real-time absolute encoder data acquisition, angular computation, and continuous monitoring in a scientific observatory environment.**

<br/>

<img src="https://img.shields.io/badge/PYTHON-DESKTOP%20APPLICATION-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/GUI-wxPython-2563EB?style=for-the-badge"/>
<img src="https://img.shields.io/badge/PLATFORM-WINDOWS-0078D6?style=for-the-badge&logo=windows&logoColor=white"/>
<img src="https://img.shields.io/badge/DOMAIN-SCIENTIFIC%20INSTRUMENTATION-0891B2?style=for-the-badge"/>

<br/><br/>

<img src="assets/encoder-face-scan.gif" width="85%" alt="Animated encoder data acquisition visualization"/>

<sub>Precision in measurement. Intelligence in processing. Reliability in operation.</sub>

</div>

---

## ◈ 01 — Project Vision

**17-Bit Absolute Encoder Data Acquisition System** is a Python-based desktop application developed during an internship at the **Indian Institute of Astrophysics (IIA), Vainu Bappu Observatory (VBO), Kavalur**.

The application was designed to acquire, process, convert, and monitor encoder data in a real-world scientific environment.

It bridges the gap between physical instrumentation and software by transforming raw encoder signals into meaningful angular measurements through a continuous acquisition and processing workflow.

The project focuses on:

- Real-time data acquisition.
- Accurate encoder data processing.
- Angular measurement conversion.
- Direction detection.
- Continuous application monitoring.
- Reliable hardware–software interaction.

> Not just collecting data. Turning physical measurements into meaningful information.

## ◈ 02 — The Intelligence Behind the System

<div align="center">

| <img src="https://img.shields.io/badge/01-DATA%20ACQUISITION-22D3EE?style=for-the-badge"/> | <img src="https://img.shields.io/badge/02-GRAY%20CODE%20PROCESSING-38BDF8?style=for-the-badge"/> |
|---|---|
| Continuous acquisition of encoder readings. | Conversion of Gray Code into binary representation. |

| <img src="https://img.shields.io/badge/03-ANGULAR%20COMPUTATION-8B5CF6?style=for-the-badge"/> | <img src="https://img.shields.io/badge/04-DIRECTION%20DETECTION-06B6D4?style=for-the-badge"/> |
|---|---|
| Calculation of decimal angle and DMS values. | Identification of clockwise, counter-clockwise and stationary movement. |

| <img src="https://img.shields.io/badge/05-LIVE%20MONITORING-10B981?style=for-the-badge"/> | <img src="https://img.shields.io/badge/06-CONNECTION%20MANAGEMENT-F472B6?style=for-the-badge"/> |
|---|---|
| Continuous visualization of processed readings. | Connection monitoring and recovery support. |

</div>

## ◈ 03 — Inside the Data Processing Pipeline

<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=16&pause=1000&color=22D3EE&center=true&vCenter=true&width=700&lines=FROM+ENCODER+SIGNAL+TO+ANGULAR+INTELLIGENCE.;EVERY+READING+HAS+A+PROCESS.;DATA+IN.+PRECISION+OUT." alt="Animated processing pipeline title"/>

</div>

### The processing stages

**01 — Acquisition**

Collect encoder data through the connected acquisition interface.

**02 — Signal Processing**

Interpret the acquired digital signal.

**03 — Gray Code Conversion**

Transform the Gray Code representation into its corresponding binary value.

**04 — Decimal Conversion**

Convert the processed binary value into its decimal representation.

**05 — Angular Computation**

Calculate the angular position represented by the encoder reading.

**06 — DMS Representation**

Express the calculated angle in Degrees, Minutes and Seconds.

**07 — Direction Analysis**

Compare successive readings to determine movement direction.

**08 — Live Visualization**

Display the latest processed readings through the desktop application.

## ◈ 04 — System Architecture

<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Orbitron&weight=500&size=15&pause=900&color=38BDF8&center=true&vCenter=true&width=650&lines=THE+ARCHITECTURE+OF+REAL-TIME+ACQUISITION.;A+CONNECTED+SOFTWARE+WORKFLOW." alt="Architecture animation"/>

</div>

```mermaid
flowchart TD
    A["ABSOLUTE ENCODER"] --> B["HARDWARE ACQUISITION INTERFACE"]
    B --> C["ACQUISITION CONTROLLER"]
    C --> D["RAW ENCODER DATA"]
    D --> E["GRAY CODE PROCESSING"]
    E --> F["BINARY CONVERSION"]
    F --> G["DECIMAL VALUE"]
    G --> H["ANGULAR COMPUTATION"]
    H --> I["DMS CONVERSION"]
    G --> J["DIRECTION DETECTION"]
    I --> K["LIVE MONITORING GUI"]
    J --> K
    C --> L["CONNECTION MONITORING"]
    L --> M["ERROR HANDLING & RECOVERY"]
    M --> C
    K --> N["APPLICATION LOGGING"]

    style A fill:#082F49,stroke:#22D3EE,color:#FFFFFF
    style E fill:#172554,stroke:#38BDF8,color:#FFFFFF
    style H fill:#312E81,stroke:#A78BFA,color:#FFFFFF
    style K fill:#164E63,stroke:#22D3EE,color:#FFFFFF
    style M fill:#064E3B,stroke:#34D399,color:#FFFFFF
```

## ◈ 05 — Technology Arsenal

<div align="center">

| Layer | Technology |
|---|---|
| Programming Language | Python |
| Desktop Interface | wxPython |
| Operating Environment | Windows |
| Data Acquisition | Digital hardware interface |
| Data Processing | Gray Code and Binary Conversion |
| Angular Measurement | Decimal Degrees and DMS |
| Configuration | INI-based configuration |
| Application Monitoring | Python Logging |
| Integration | Hardware–Software Interface |

<br/>

<img src="https://skillicons.dev/icons?i=python,windows&theme=dark" alt="Technology icons"/>

</div>

## ◈ 06 — Application Experience

The desktop application provides a dedicated interface for observing encoder readings and monitoring the acquisition process.

Key interface capabilities include:

- Live encoder readings.
- Angular position display.
- Degree-Minute-Second representation.
- Movement direction indication.
- Hardware connection status.
- Application date and time.
- Continuous acquisition monitoring.

<div align="center">

<img src="assets/application-dashboard.png" width="90%" alt="Live encoder application dashboard"/>

<sub>Figure 01 — Live Encoder Data Acquisition Dashboard</sub>

<br/><br/>

<img src="assets/hardware-initialization.png" width="90%" alt="Application initialization screen"/>

<sub>Figure 02 — Application Startup and Hardware Initialization</sub>

<br/><br/>

<img src="assets/real-time-monitoring.png" width="90%" alt="Continuous encoder monitoring"/>

<sub>Figure 03 — Continuous Real-Time Encoder Monitoring</sub>

</div>

## ◈ 07 — Engineering for Reliability

A real-world hardware application must do more than produce readings. It must also handle interruptions and maintain predictable operation.

Verifiably implemented application capabilities include:

| Capability | Purpose |
|---|---|
| Hardware Detection | Identify hardware availability during initialization. |
| Connection Monitoring | Observe the acquisition connection status. |
| Automatic Reconnection | Recover from supported temporary interruptions. |
| Logging | Record application events and troubleshooting information. |
| Configuration | Maintain application settings separately. |
| Graceful Shutdown | Close application resources cleanly. |
| Direction Handling | Account for movement across the angular boundary. |

## ◈ 08 — Testing & Validation

The developed application was tested in the actual observatory hardware environment.

The testing process covered:

- Application startup and initialization.
- Hardware recognition.
- Data acquisition.
- Gray Code processing and conversion.
- Angle and DMS calculations.
- Direction identification.
- Stationary encoder behaviour.
- Continuous monitoring.
- Connection handling.
- GUI operation and stability.

A particularly rewarding part of the project was observing the application communicate successfully with the physical hardware and display processed readings in real time.

## ◈ 09 — Project Gallery

<div align="center">

<img src="assets/observatory-environment.jpg" width="85%" alt="Observatory internship environment"/>

<sub>Figure 04 — Scientific Environment at Vainu Bappu Observatory</sub>

<br/><br/>

<img src="assets/project-hardware.jpg" width="85%" alt="Project hardware setup"/>

<sub>Figure 05 — Project Testing Environment</sub>

<br/><br/>

<img src="assets/application-output.png" width="85%" alt="Actual application output"/>

<sub>Figure 06 — Application Output</sub>

</div>

## ◈ 10 — Running the Application

### Prerequisites

- Windows 10 or Windows 11.
- Python installed and configured.
- Required Python dependencies.
- wxPython.
- Compatible acquisition hardware and its authorised runtime environment.

### 01 — Clone the repository

```bash
git clone https://github.com/<YOUR_USERNAME>/<YOUR_REPOSITORY>.git
cd <YOUR_REPOSITORY>
```

### 02 — Create a virtual environment

```bash
python -m venv venv
```

### 03 — Activate the environment

**Windows**

```bash
venv\Scripts\activate
```

### 04 — Install the dependencies

```bash
pip install -r requirements.txt
```

### 05 — Launch the application

```bash
python encoder_daq_single.py
```

> **Note:** Full data acquisition functionality requires the compatible hardware environment. The application should be operated only with the authorised runtime and configuration.

## ◈ 11 — Learning Outcomes

This project provided practical experience in several engineering areas:

- Python application development.
- Desktop GUI engineering.
- Hardware–software integration.
- Real-time data acquisition.
- Digital data representation.
- Gray Code and binary conversion.
- Angular measurement systems.
- Direction detection algorithms.
- Connection management and recovery.
- Logging and debugging.
- Testing applications with physical hardware.

It also provided valuable exposure to the challenges of developing software for a scientific research environment.

## ◈ 12 — Project Information

<div align="center">

| Detail | Information |
|---|---|
| Project | 17-Bit Absolute Encoder Data Acquisition System |
| Organization | Indian Institute of Astrophysics |
| Location | Vainu Bappu Observatory, Kavalur |
| Application | Desktop Data Acquisition System |
| Language | Python |
| GUI Framework | wxPython |
| Domain | Scientific Instrumentation |
| Focus | Real-Time Data Processing and Monitoring |

</div>

## ◈ 13 — Future Scope

- Enhanced hardware diagnostics.
- Improved acquisition monitoring.
- Extended data visualization.
- Additional export and reporting capabilities.
- Further improvements to configuration management.
- Expanded system validation and testing.

## ◈ 14 — Confidentiality Notice

This repository presents the project at an academic and software-development level.

Certain internal hardware specifications, communication configurations, driver implementation details, and other organization-specific information have intentionally been omitted to respect institutional confidentiality.

The README is not intended to document or disclose proprietary observatory infrastructure.

## ◈ 15 — Acknowledgement

I sincerely thank the **Indian Institute of Astrophysics (IIA), Vainu Bappu Observatory, Kavalur**, for providing the opportunity to work on a practical scientific software development project.

My heartfelt gratitude to **Mrs. Vellai Selvi (Engineer D)** for her guidance, encouragement, and support throughout the internship.

---

<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Orbitron&weight=600&size=21&duration=2600&pause=850&color=22D3EE&center=true&vCenter=true&width=800&lines=FROM+SIGNALS+TO+MEANINGFUL+DATA.;ENGINEERED+FOR+PRECISION.;BUILT+WITH+PYTHON.;INSPIRED+BY+SCIENCE." alt="Animated closing message"/>

<br/><br/>

**ENGINEERING × SCIENCE × SOFTWARE**

<sub>17-Bit Absolute Encoder Data Acquisition System</sub>

<br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:06B6D4,50:075985,100:020617&height=140&section=footer&animation=fadeIn" width="100%" alt="Animated cyan footer"/>

</div>
