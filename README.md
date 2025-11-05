# CARINA - Controlled Artificial Road-traffic Intelligence Network Architecture

**CARINA** is a cutting-edge, open-source software ecosystem designed to act as a digital "brain" for a city's traffic light network. Its mission is to replace fixed-time control systems with a network of coordinated, adaptive, and safe Artificial Intelligence (AI) agents that optimize traffic flow in real-time.

Conceived as a digital public good, the project aims to democratize access to smart city technologies, with the core objectives of reducing congestion, decreasing pollution, and increasing safety at intersections.

---

### Key Capabilities

CARINA operates on two main fronts:

1.  **Simulation and Planning Tool:** For traffic engineers and public managers, CARINA acts as a "virtual laboratory." Using the **SUMO traffic simulator**, it allows the creation of a "digital twin" of the road network to test the impact of infrastructure changes, compare control strategies, and make data-driven planning decisions. It includes an **Infrastructure Analysis Service (SAS)** that evaluates intersections and recommends the addition, maintenance, or removal of traffic lights based on traffic engineering warrants.

2.  **Intelligent Control System:** This is its primary function. CARINA employs a team of AI agents to manage the traffic light network. These agents learn and execute a control policy aimed at maximizing fluidity and safety, dynamically adapting to traffic conditions.

---

### Architecture: A Resilient Microservices Ecosystem

To ensure stability and scalability, CARINA is built on a microservices architecture, where each component runs in its own OS process and communicates asynchronously.

-   **Launcher (`carina.py`):** The heart of the system, this entry point starts, manages, and terminates all other processes, ensuring the entire ecosystem functions cohesively.
-   **Central Controller (`central_controller.py`):** The system's hub. It manages the connection to the SUMO simulator and serves as the single source of truth for the simulation state. It receives commands from the AI and the UI, applies them to the simulation, and distributes updated data packets to all other services.
-   **AI Process (`main.py`):** An isolated process where all reinforcement learning and AI decision-making logic is executed. This isolation ensures that the high workload of the AI does not affect the simulation's stability.
-   **Watchdog (`watchdog.py`):** A failsafe security mechanism. If the AI Process becomes unresponsive, the Central Controller ignores it and follows the commands of the Watchdog, which continuously sends a safe, fixed-time traffic light plan.
-   **Support Services:**
    -   **Dashboard Service (SDS):** Streams real-time data to the user interface.
    -   **Infrastructure Analysis Service (SAS):** Accumulates long-term traffic data to generate reports on traffic light necessity.
    -   **Database Worker:** Asynchronously saves metrics and reports to an SQLite database.
    -   **XAI Worker:** An on-demand service that performs "Explainable AI" analysis without impacting simulation performance.

---

### The AI Brain: The GOMES Architecture

CARINA's decision-making core is the **GOMES (Graph-based Operational Multi-agent Expert System) Architecture**, a hybrid, multi-agent AI system:

-   **Local Agent (PPO + LSTM):** The tactical controller for each traffic light. It uses a neural network with memory (LSTM) and learns via the Proximal Policy Optimization (PPO) algorithm to optimize local traffic flow.
-   **Guardian Agent (Dueling DQN):** A safety specialist that operates asynchronously. It analyzes traffic states to identify and prevent imminent risk situations, sending veto signals to the main system.
-   **Strategist (GAT Lite):** A Graph Attention Network (GAT) that analyzes the traffic light network as a graph. It provides global network awareness to each Local Agent, enabling large-scale coordination to prevent cascading congestion.

---

### Training and Safety: The DA SILVA Piloting System

To ensure the AI is reliable before controlling real traffic, CARINA uses the **DA SILVA (Dynamic Agent Safety Integrated Learning for Validated Autonomy) Piloting System**. This system acts as a "driving school" that subjects the agents to a rigorous, phased training and validation process:

1.  **Child:** The agent only observes the fixed-time system and learns from it.
2.  **Teen:** The agent is allowed to control traffic during off-peak hours.
3.  **Adult:** After proving superior performance and high confidence in its decisions, the agent "graduates" and is granted full autonomy.

---

### The User Interface

The UI is a comprehensive desktop application that serves as the system's control and visualization panel, organized into three main tabs:

-   **Operational Dashboard:** For real-time monitoring and control, featuring a congestion heatmap and detailed data for every street and traffic light.
-   **Planning & Optimization:** A tool for traffic engineers, displaying analysis recommendations and allowing the generation of technical reports.
-   **Diagnostics & System:** Tools for developers and researchers, including a real-time log viewer, an **Explainable AI (XAI)** feature powered by Captum to analyze agent decisions, and a system summary.# CARINA
# CARINA
