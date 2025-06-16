# Hardness Measurement SPC Desktop Application
## Project Overview
This project is a compact Windows desktop application designed to streamline the process of collecting, validating, and visualizing hardness measurement data for product samples. Developed for a specific one-time project aimed at accumulating 3,000 hardness values for Quality and R&D evaluation, this application ensures data integrity and provides immediate statistical insights to technicians.

### Key Features
- Intuitive Data Entry UI:

    - Provides a user-friendly interface for employees (technicians) to input hardness measurements for various product samples.

    - Features clearly organized input fields for "Tech Initials," "Sample ID," and twelve individual hardness readings (six "Bottom" and six "Top").

    - Supports efficient data entry using Tab key navigation between input fields.

- Robust Data Validation:

    - Tech Initials: Enforces a character length of 2 to 4 characters.

    - Sample ID: Validates against a strict format of "XXX-YY" (e.g., "123-ab").

    - Hardness Values: Ensures all 12 individual hardness measurements are numerical values between 100 and 500 (inclusive).

    - Real-time Error Feedback: Displays immediate and clear pop-up error messages when data does not meet the specified validation criteria, guiding technicians to correct inputs.

- MSSQL Database Integration:

    - Seamlessly connects to and saves validated hardness measurement data into an MSSQL database.

    - Ensures persistent storage of all collected historical measurements.

- Dynamic SPC Charting:

    - Graphically displays accumulative hardness measurements on two dedicated charts (one for "Bottom" and one for "Top"). The charts update automatically when new data is prepared for saving.

    - Statistical Process Control (SPC): Dynamically calculates and displays crucial SPC values on the charts:

        - Upper Control Limit (UCL)

        - Mean

        - Lower Control Limit (LCL)

    - Adaptive Control Limits: SPC limits are continuously updated based on all previously saved measurements in the database, providing a living statistical overview.

    - Default Limits: In the edge case of an empty database (no historical data), the application intelligently utilizes hardcoded default SPC values (Top/Bottom UCL = 340, Mean = 320, LCL = 300) to ensure the charts are never blank and provide initial guidance.

- Pre-Save Quality Control:

    - Includes a critical validation step that checks if the current hardness values fall within the updated UCL and LCL before allowing the data to be saved to the database. This acts as a real-time alert system, notifying quality personnel if measurements are out of specification.

    - Utilizes a two-step "Display on Graph" and "Save to Database" workflow, allowing technicians to visually review data and SPC limits before committing entries to the database.

### Technologies Used
- Python 3.x: The core programming language.

- Tkinter: For creating the graphical user interface (GUI) of the desktop application.

- Matplotlib: For plotting and displaying the hardness measurement graphs and SPC limits.

- NumPy: For efficient numerical operations, particularly in calculating mean and standard deviation for SPC.

- pyodbc: For connecting to and interacting with the MSSQL database.

- re (Python's built-in re module): For regular expression-based validation of the Sample ID.

### AI Assistance in Development
This project was developed with the assistance of Gemini, an advanced AI model. This collaboration demonstrates the ability to effectively leverage AI tools to enhance development efficiency and explore complex feature implementations, showcasing a modern approach to software engineering.

### Setup and How to Run
To set up and run this application on your Windows machine, follow these steps:

1. Prerequisites:

    - Python 3.x: Ensure Python is installed on your system. You can download it from [python.org](https://www.python.org/).

    - Python Libraries: Install the required Python packages via pip:

        ```
        pip install pyodbc numpy matplotlib
        ```

    - ODBC Driver for SQL Server: Download and install the appropriate Microsoft ODBC Driver for SQL Server (e.g., "ODBC Driver 17 for SQL Server") for your Windows version. This is crucial for `pyodbc` to connect to MSSQL. You can find it on Microsoft's official documentation or download pages.

2. Database Setup (MSSQL):

    - Ensure you have an MSSQL Server instance accessible.

    - The application will attempt to create a table named `HardnessReadings` if it doesn't exist. This table will have columns for `TechnicianInitials`, `SampleID`, `TopOrBottom`, `Position`, `HardnessValue`, and `Timestamp`.

3. Configure Database Connection:

    - Open the `Hardness_UI_Application.py` file (or whatever you name the script) in a text editor.

    - Locate the `DB_CONFIG` dictionary at the top of the file:

        ```
        DB_CONFIG = {
            'server': 'YOUR_SERVER_NAME',      # e.g., 'localhost\SQLEXPRESS' or 'your_server_ip'
            'database': 'YOUR_DATABASE_NAME',  # e.g., 'HardnessData'
            'username': 'YOUR_USERNAME',       # e.g., 'sa'
            'password': 'YOUR_PASSWORD'        # e.g., 'YourStrongPassword123'
        }
        ```

    - Replace the placeholder values with your actual SQL Server details (server name/IP, database name, username, and password).

4. Run the Application:

    - Open a Command Prompt or PowerShell window.

    - Navigate to the directory where you saved the Python script (`Hardness_UI_Application.py`).

    - Execute the script using:

        ```
        python Hardness_UI_Application.py
        ```

    - The Tkinter desktop application window should appear, ready for use.

### Project Motivation
This application was developed as a crucial tool for a specialized, one-time project within the Quality and Research & Development (R&D) groups of our client. The primary goal is to accumulate precisely 3,000 hardness values from product samples. These accumulated measurements will then be comprehensively evaluated by the Quality and R&D teams to assess product performance, identify trends, and make informed decisions.

The application ensures the reliability of the collected data through rigorous input validations and provides real-time visual feedback on statistical process control. This immediate insight into the measurements against established control limits is vital for maintaining quality standards throughout the data collection phase, allowing for prompt intervention if any values fall outside the expected range.