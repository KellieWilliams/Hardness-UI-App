import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pyodbc # For MSSQL database connection
import numpy as np # For statistical calculations
from tkinter import font # Import the font module
import re # Import the regular expression module for Sample ID validation

# Global variables for the matplotlib figure and axes
fig = None
ax_bottom = None # Axis for Bottom Hardness
ax_top = None    # Axis for Top Hardness
canvas_widget = None

# Global variables to temporarily store data between "Display" and "Save" actions
_pending_records_to_save = []
_current_displayed_bottom_values = []
_current_displayed_top_values = []

# --- MSSQL Database Configuration ---
# IMPORTANT: Replace these with your actual SQL Server details
DB_CONFIG = {
    'server': 'YOUR_SERVER_NAME',      # e.g., 'localhost\SQLEXPRESS' or 'your_server_ip'
    'database': 'YOUR_DATABASE_NAME',  # e.g., 'HardnessData'
    'username': 'YOUR_USERNAME',       # e.g., 'sa'
    'password': 'YOUR_PASSWORD'        # e.g., 'YourStrongPassword123'
}

TABLE_NAME = "HardnessReadings"

# --- Default SPC Values for initial empty database scenario ---
DEFAULT_TOP_UCL = 340.0
DEFAULT_TOP_MEAN = 320.0
DEFAULT_TOP_LCL = 300.0

DEFAULT_BOTTOM_UCL = 340.0
DEFAULT_BOTTOM_MEAN = 320.0
DEFAULT_BOTTOM_LCL = 300.0


def connect_db():
    """Establishes a connection to the MSSQL database."""
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"UID={DB_CONFIG['username']};"
        f"PWD={DB_CONFIG['password']}"
    )
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        messagebox.showerror("Database Connection Error", f"Failed to connect to database: {sqlstate}\n{ex}")
        return None

def create_table_if_not_exists():
    """Creates the HardnessReadings table if it does not exist."""
    conn = connect_db()
    if conn:
        cursor = conn.cursor()
        try:
            # SQL to create table with columns: Technician Initials, Sample ID, Top/Bottom, Position, Hardness Value, Timestamp
            # Using NVARCHAR for text fields and FLOAT for hardness value, DATETIME for timestamp
            cursor.execute(f"""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{TABLE_NAME}' and xtype='U')
                CREATE TABLE {TABLE_NAME} (
                    ID INT PRIMARY KEY IDENTITY(1,1),
                    TechnicianInitials NVARCHAR(50) NOT NULL,
                    SampleID NVARCHAR(100) NOT NULL,
                    TopOrBottom NVARCHAR(10) NOT NULL,
                    Position INT NOT NULL,
                    HardnessValue FLOAT NOT NULL,
                    Timestamp DATETIME DEFAULT GETDATE()
                ); -- Added semicolon
            """)
            conn.commit()
            print(f"Table '{TABLE_NAME}' checked/created successfully.")
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to create table: {e}")
            conn.rollback()
        finally:
            conn.close()

def get_all_hardness_values():
    """Retrieves all historical hardness values from the database, separated by Top/Bottom."""
    conn = connect_db()
    bottom_hardness_values = []
    top_hardness_values = []
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT HardnessValue, TopOrBottom FROM {TABLE_NAME} ORDER BY Timestamp ASC;") # Added semicolon
            for row in cursor.fetchall():
                value, category = row
                if category == 'Bottom':
                    bottom_hardness_values.append(value)
                elif category == 'Top':
                    top_hardness_values.append(value)
            print(f"Retrieved {len(bottom_hardness_values)} historical Bottom values and {len(top_hardness_values)} historical Top values.")
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to retrieve historical data: {e}")
        finally:
            conn.close()
    return bottom_hardness_values, top_hardness_values

def calculate_control_limits(data):
    """
    Calculates the mean, Upper Control Limit (UCL), and Lower Control Limit (LCL)
    based on the provided data using 3-sigma limits (mean +/- 3 * standard deviation).

    Args:
        data (list): A list of numerical hardness values.

    Returns:
        tuple: (mean, ucl, lcl) or (None, None, None) if not enough data.
    """
    if len(data) < 2: # Need at least 2 points to calculate std dev for sample std.
                      # If 1 point, std dev is 0, which also doesn't make sense for limits.
        return None, None, None

    mean_val = np.mean(data)
    std_dev = np.std(data, ddof=1) # ddof=1 for sample standard deviation

    ucl = mean_val + (3 * std_dev)
    lcl = mean_val - (3 * std_dev)

    return mean_val, ucl, lcl


def create_plot_area():
    """
    Creates and embeds the matplotlib plot area into the Tkinter window.
    Initializes two empty plots: one for Bottom and one for Top hardness.
    """
    global fig, ax_bottom, ax_top, canvas_widget

    # Create a matplotlib figure with two subplots (2 rows, 1 column)
    # Changed figsize height from 8 to 4 (half as tall)
    fig, (ax_bottom, ax_top) = plt.subplots(2, 1, figsize=(6, 4))

    # Configure Bottom Hardness plot
    ax_bottom.set_title('Bottom Hardness Readings')
    ax_bottom.set_xlabel('Position')
    ax_bottom.set_ylabel('Hardness - BHN') # Updated label
    ax_bottom.grid(True)
    ax_bottom.set_ylim(bottom=0) # Ensure y-axis starts from 0 or a reasonable minimum

    # Configure Top Hardness plot
    ax_top.set_title('Top Hardness Readings')
    ax_top.set_xlabel('Position')
    ax_top.set_ylabel('Hardness - BHN') # Updated label
    ax_top.grid(True)
    ax_top.set_ylim(bottom=0) # Ensure y-axis starts from 0 or a reasonable minimum

    fig.tight_layout(pad=3.0) # Adjust layout to prevent titles/labels from overlapping

    # Embed the matplotlib figure into the Tkinter window
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas_widget = canvas.get_tk_widget()
    # Place the canvas below the input fields and button
    canvas_widget.grid(row=root.grid_size()[1], column=0, columnspan=num_display_columns, padx=10, pady=10, sticky="nsew")
    canvas.draw()

def update_plot(current_bottom_values, current_top_values,
                mean_bottom, ucl_bottom, lcl_bottom,
                mean_top, ucl_top, lcl_top):
    """
    Updates the two line graphs with the new hardness values and separate control limits.

    Args:
        current_bottom_values (list): A list of 6 float values for current Bottom Hardness.
        current_top_values (list): A list of 6 float values for current Top Hardness.
        mean_bottom (float): The calculated mean for Bottom values.
        ucl_bottom (float): The calculated UCL for Bottom values.
        lcl_bottom (float): The calculated LCL for Bottom values.
        mean_top (float): The calculated mean for Top values.
        ucl_top (float): The calculated UCL for Top values.
        lcl_top (float): The calculated LCL for Top values.
    """
    global ax_bottom, ax_top, fig

    if ax_bottom is None or ax_top is None:
        create_plot_area() # Recreate if not initialized (shouldn't happen)

    # Clear previous plots
    ax_bottom.clear()
    ax_top.clear()

    # X-axis labels for positions 1-6
    x_labels = [f"{i+1}" for i in range(6)]
    x_positions = range(6)

    # --- Plot for Bottom Hardness ---
    ax_bottom.plot(x_positions, current_bottom_values, marker='o', linestyle='-', color='skyblue', label='Current Reading')
    ax_bottom.set_title('Bottom Hardness Readings')
    ax_bottom.set_xlabel('Position')
    ax_bottom.set_ylabel('Hardness - BHN') # Updated label
    ax_bottom.grid(True)

    # Add control limits and mean to Bottom plot if available
    if ucl_bottom is not None and lcl_bottom is not None:
        ax_bottom.axhline(y=mean_bottom, color='blue', linestyle=':', label=f'Mean ({mean_bottom:.2f})')
        ax_bottom.axhline(y=ucl_bottom, color='red', linestyle='--', label=f'UCL ({ucl_bottom:.2f})')
        ax_bottom.axhline(y=lcl_bottom, color='red', linestyle='--', label=f'LCL ({lcl_bottom:.2f})')
        ax_bottom.legend(loc='best') # Add a legend for the lines

    # Adjust y-limits for Bottom plot based on its data and limits
    # Include current values and its specific control limits for y-axis scaling
    all_bottom_data_for_ylim = list(current_bottom_values)
    if ucl_bottom is not None:
        all_bottom_data_for_ylim.extend([ucl_bottom, lcl_bottom, mean_bottom])
    if all_bottom_data_for_ylim:
        min_val_bottom = min(all_bottom_data_for_ylim)
        max_val_bottom = max(all_bottom_data_for_ylim)
        padding_bottom = (max_val_bottom - min_val_bottom) * 0.1 if (max_val_bottom - min_val_bottom) > 0 else 1
        ax_bottom.set_ylim(min(0, min_val_bottom - padding_bottom), max_val_bottom + padding_bottom)
    else:
        # Default y-limits if no data or limits to display
        ax_bottom.set_ylim(DEFAULT_BOTTOM_LCL - 10, DEFAULT_BOTTOM_UCL + 10)


    # --- Plot for Top Hardness ---
    ax_top.plot(x_positions, current_top_values, marker='o', linestyle='-', color='lightcoral', label='Current Reading')
    ax_top.set_title('Top Hardness Readings')
    ax_top.set_xlabel('Position')
    ax_top.set_ylabel('Hardness - BHN') # Updated label
    ax_top.grid(True)

    # Add control limits and mean to Top plot if available
    if ucl_top is not None and lcl_top is not None:
        ax_top.axhline(y=mean_top, color='blue', linestyle=':', label=f'Mean ({mean_top:.2f})')
        ax_top.axhline(y=ucl_top, color='red', linestyle='--', label=f'UCL ({ucl_top:.2f})')
        ax_top.axhline(y=lcl_top, color='red', linestyle='--', label=f'LCL ({lcl_top:.2f})')
        ax_top.legend(loc='best') # Add a legend for the lines

    # Adjust y-limits for Top plot based on its data and limits
    all_top_data_for_ylim = list(current_top_values)
    if ucl_top is not None:
        all_top_data_for_ylim.extend([ucl_top, lcl_top, mean_top])
    if all_top_data_for_ylim:
        min_val_top = min(all_top_data_for_ylim)
        max_val_top = max(all_top_data_for_ylim)
        padding_top = (max_val_top - min_val_top) * 0.1 if (max_val_top - min_val_top) > 0 else 1
        ax_top.set_ylim(min(0, min_val_top - padding_top), max_val_top + padding_top)
    else:
        # Default y-limits if no data or limits to display
        ax_top.set_ylim(DEFAULT_TOP_LCL - 10, DEFAULT_TOP_UCL + 10)


    fig.tight_layout(pad=3.0) # Adjust layout again after plotting
    fig.canvas.draw() # Redraw the canvas with the updated plots


def display_on_graph():
    """
    Retrieves data from all input fields, validates it, and updates the graphs
    with the current readings and SPC limits. Prepares data for saving.
    """
    global _pending_records_to_save, _current_displayed_bottom_values, _current_displayed_top_values

    # Reset pending records and plot values
    _pending_records_to_save = []
    _current_displayed_bottom_values = []
    _current_displayed_top_values = []

    # Get the values from all input fields
    technician_initials = entry_technician_initials.get().strip()
    sample_id = entry_sample_id.get().strip()
    bottom_hardness_raw = [entry_bottom_hardness[i].get().strip() for i in range(6)]
    top_hardness_raw = [entry_top_hardness[i].get().strip() for i in range(6)]

    # Basic validation for Technician Initials length
    if not (2 <= len(technician_initials) <= 4):
        messagebox.showerror("Input Error", "Tech Initials must be between 2 and 4 characters long.")
        button_save_to_db['state'] = tk.DISABLED
        return
    
    # Validation for Sample ID format: three chars, hyphen, two chars (e.g., 123-ab)
    sample_id_pattern = re.compile(r"^.{3}-.{2}$")
    if not sample_id_pattern.match(sample_id):
        messagebox.showerror("Input Error", "Sample ID must be in the format 'XXX-YY' (e.g., '123-ab').")
        button_save_to_db['state'] = tk.DISABLED
        return

    # Process Bottom Hardness values
    for i, val_str in enumerate(bottom_hardness_raw):
        if not val_str:
            messagebox.showerror("Input Error", f"Bottom {i+1} Hardness is empty!")
            button_save_to_db['state'] = tk.DISABLED
            return
        try:
            hardness_value = float(val_str)
            # Hardness value range validation
            if not (100 <= hardness_value <= 500):
                messagebox.showerror("Input Error", f"Bottom {i+1} Hardness must be between 100 and 500.")
                button_save_to_db['state'] = tk.DISABLED
                return
            record = (technician_initials, sample_id, 'Bottom', i + 1, hardness_value)
            _pending_records_to_save.append(record)
            _current_displayed_bottom_values.append(hardness_value)
        except ValueError:
            messagebox.showerror("Input Error", f"Bottom {i+1} Hardness must be a valid number!")
            button_save_to_db['state'] = tk.DISABLED
            return

    # Process Top Hardness values
    for i, val_str in enumerate(top_hardness_raw):
        if not val_str:
            messagebox.showerror("Input Error", f"Top {i+1} Hardness is empty!")
            button_save_to_db['state'] = tk.DISABLED
            return
        try:
            hardness_value = float(val_str)
            # Hardness value range validation
            if not (100 <= hardness_value <= 500):
                messagebox.showerror("Input Error", f"Top {i+1} Hardness must be between 100 and 500.")
                button_save_to_db['state'] = tk.DISABLED
                return
            record = (technician_initials, sample_id, 'Top', i + 1, hardness_value)
            _pending_records_to_save.append(record)
            _current_displayed_top_values.append(hardness_value)
        except ValueError:
            messagebox.showerror("Input Error", f"Top {i+1} Hardness must be a valid number!")
            button_save_to_db['state'] = tk.DISABLED
            return

    # --- Retrieve All Data and Calculate/Set Plots with separate SPC limits ---
    all_historical_bottom_values, all_historical_top_values = get_all_hardness_values()

    # Calculate limits for Bottom
    mean_bottom, ucl_bottom, lcl_bottom = calculate_control_limits(all_historical_bottom_values)
    # If no data or not enough data, use default values
    if ucl_bottom is None:
        mean_bottom, ucl_bottom, lcl_bottom = DEFAULT_BOTTOM_MEAN, DEFAULT_BOTTOM_UCL, DEFAULT_BOTTOM_LCL
        print("Using default Bottom SPC limits.") # For debugging

    # Calculate limits for Top
    mean_top, ucl_top, lcl_top = calculate_control_limits(all_historical_top_values)
    # If no data or not enough data, use default values
    if ucl_top is None:
        mean_top, ucl_top, lcl_top = DEFAULT_TOP_MEAN, DEFAULT_TOP_UCL, DEFAULT_TOP_LCL
        print("Using default Top SPC limits.") # For debugging


    update_plot(_current_displayed_bottom_values, _current_displayed_top_values,
                mean_bottom, ucl_bottom, lcl_bottom,
                mean_top, ucl_top, lcl_top)

    messagebox.showinfo("Display Success", "Data displayed on graph. Please review before saving to database.")
    # Enable the save button once all validations pass and data is prepared for saving
    button_save_to_db['state'] = tk.NORMAL


def save_to_database():
    """
    Saves the currently displayed data (stored in _pending_records_to_save) to the MSSQL database.
    """
    global _pending_records_to_save, _current_displayed_bottom_values, _current_displayed_top_values

    if not _pending_records_to_save:
        messagebox.showwarning("Save Error", "No data to save. Please display on graph first.")
        return

    # --- Database Insertion ---
    conn = connect_db()
    if conn:
        cursor = conn.cursor()
        try:
            insert_sql = f"""
                INSERT INTO {TABLE_NAME} (TechnicianInitials, SampleID, TopOrBottom, Position, HardnessValue)
                VALUES (?, ?, ?, ?, ?); -- Added semicolon
            """
            cursor.executemany(insert_sql, _pending_records_to_save)
            conn.commit()
            messagebox.showinfo("Database Save", f"Successfully saved {len(_pending_records_to_save)} records to MSSQL.")
            print(f"Saved records: {_pending_records_to_save}")

            # Clear the input fields after successful saving
            entry_technician_initials.delete(0, tk.END)
            entry_sample_id.delete(0, tk.END)
            for i in range(6):
                entry_bottom_hardness[i].delete(0, tk.END)
                entry_top_hardness[i].delete(0, tk.END)

            # Clear temporary data storage after saving
            _pending_records_to_save = []
            _current_displayed_bottom_values = []
            _current_displayed_top_values = []

            # Re-fetch all historical data and update plots to reflect new limits
            # (current plot values will be empty lists since input fields are cleared)
            all_historical_bottom_values, all_historical_top_values = get_all_hardness_values()
            
            # Recalculate limits with potentially new data, then apply defaults if still insufficient
            mean_bottom, ucl_bottom, lcl_bottom = calculate_control_limits(all_historical_bottom_values)
            if ucl_bottom is None:
                mean_bottom, ucl_bottom, lcl_bottom = DEFAULT_BOTTOM_MEAN, DEFAULT_BOTTOM_UCL, DEFAULT_BOTTOM_LCL
                print("Using default Bottom SPC limits after save.") # For debugging

            mean_top, ucl_top, lcl_top = calculate_control_limits(all_historical_top_values)
            if ucl_top is None:
                mean_top, ucl_top, lcl_top = DEFAULT_TOP_MEAN, DEFAULT_TOP_UCL, DEFAULT_TOP_LCL
                print("Using default Top SPC limits after save.") # For debugging

            update_plot([], [], # Pass empty lists for current values since fields are cleared
                        mean_bottom, ucl_bottom, lcl_bottom,
                        mean_top, ucl_top, lcl_top)

            button_save_to_db['state'] = tk.DISABLED # Disable save button after successful save

        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to save data to MSSQL: {e}")
            conn.rollback()
        finally:
            conn.close()
    else:
        messagebox.showwarning("Database Warning", "Could not connect to database. Data not saved.")


# Create the main application window
root = tk.Tk()
root.title("Hardness Data Entry App")
# Adjusted height to better accommodate two plots
root.geometry("800x700") # Adjusted height to 700 from 1000

# Define fonts for labels and entries
label_font = font.nametofont("TkDefaultFont")
label_font.configure(size=12) # Set label font size to 12

entry_font = font.nametofont("TkTextFont") # TkTextFont is usually for entries/text widgets
entry_font.configure(size=24) # Set entry font size to 24 (doubled for height)

# --- UI Layout Parameters ---
# Number of columns for hardness value entries (6 for B1-B6 and T1-T6)
num_hardness_cols = 6
# Total columns for display (1 for labels + num_hardness_cols for entries/spanning)
# Making it 6 columns, where Technician/Sample labels take column 0 and entries span 5 columns
num_display_columns = num_hardness_cols

# Configure grid column weights to distribute space evenly among the 6 hardness columns
for i in range(num_display_columns):
    root.grid_columnconfigure(i, weight=1)

# Initialize current_row counter
current_row = 0

# --- Tech Initials ---
label_technician_initials = tk.Label(root, text="Tech Initials:", font=label_font)
# Place label in the first column, align to the left
label_technician_initials.grid(row=current_row, column=0, padx=10, pady=5, sticky="w")
entry_technician_initials = tk.Entry(root, font=entry_font)
# Place entry in the second column and let it span across the remaining 5 columns
entry_technician_initials.grid(row=current_row, column=1, columnspan=num_hardness_cols - 1, padx=10, pady=5, sticky="ew")
current_row += 1

# --- Sample ID ---
label_sample_id = tk.Label(root, text="Sample ID:", font=label_font)
# Place label in the first column, align to the left
label_sample_id.grid(row=current_row, column=0, padx=10, pady=5, sticky="w")
entry_sample_id = tk.Entry(root, font=entry_font)
# Place entry in the second column and let it span across the remaining 5 columns
entry_sample_id.grid(row=current_row, column=1, columnspan=num_hardness_cols - 1, padx=10, pady=5, sticky="ew")
current_row += 1

# Add a small visual separator or empty row for better grouping
current_row += 1 # Add an empty row for spacing before hardness values

# --- Bottom Hardness Labels and Entries ---
# Labels for Bottom Hardness positions (B1, B2, ..., B6)
label_bottom_headers = []
for i in range(num_hardness_cols):
    label = tk.Label(root, text=f"Bottom {i+1}", font=label_font)
    # Labels directly above their respective entries
    label.grid(row=current_row, column=i, padx=5, pady=2, sticky="s")
    label_bottom_headers.append(label)
current_row += 1 # Move to the row for entries

entry_bottom_hardness = []
for i in range(num_hardness_cols):
    entry = tk.Entry(root, font=entry_font)
    # Entries aligned horizontally
    entry.grid(row=current_row, column=i, padx=5, pady=5, sticky="ew")
    entry_bottom_hardness.append(entry)
current_row += 1 # Move to the next row after Bottom entries

# --- Top Hardness Labels and Entries ---
# Labels for Top Hardness positions (T1, T2, ..., T6)
label_top_headers = []
for i in range(num_hardness_cols):
    label = tk.Label(root, text=f"Top {i+1}", font=label_font)
    # Labels directly above their respective entries, aligning with Bottom labels
    label.grid(row=current_row, column=i, padx=5, pady=2, sticky="s")
    label_top_headers.append(label)
current_row += 1 # Move to the row for entries

entry_top_hardness = []
for i in range(num_hardness_cols):
    entry = tk.Entry(root, font=entry_font)
    # Entries aligned horizontally, aligning with Bottom entries
    entry.grid(row=current_row, column=i, padx=5, pady=5, sticky="ew")
    entry_top_hardness.append(entry)
current_row += 1 # Move to the next row after Top entries

# Configure all rows to expand (except for some spacing rows)
# Assuming a reasonable number of rows will be used by the layout logic above
total_rows_for_widgets = current_row
for i in range(total_rows_for_widgets):
    root.grid_rowconfigure(i, weight=1) # Give all widget rows some weight for responsiveness

# Create a frame for buttons to easily manage their horizontal layout
button_frame = tk.Frame(root)
button_frame.grid(row=current_row, column=0, columnspan=num_display_columns, pady=10)
# Configure columns within the button frame to distribute space for buttons
button_frame.grid_columnconfigure(0, weight=1)
button_frame.grid_columnconfigure(1, weight=1)


# Create and place the "Display on Graph" button
button_display_on_graph = tk.Button(button_frame, text="Display on Graph", command=display_on_graph, font=label_font)
button_display_on_graph.grid(row=0, column=0, padx=5, pady=0, sticky="ew") # Placed in button_frame

# Create and place the "Save to Database" button (initially disabled)
button_save_to_db = tk.Button(button_frame, text="Save to Database", command=save_to_database, state=tk.DISABLED, font=label_font)
button_save_to_db.grid(row=0, column=1, padx=5, pady=0, sticky="ew") # Placed in button_frame
current_row += 1 # Increment current_row for the plot area

# Initialize the plot area with two subplots, spanning all display columns
create_plot_area() # This function will use `num_display_columns` for columnspan

# Initial database setup (create table if not exists)
create_table_if_not_exists()

# Load initial historical data and update plots on startup
initial_historical_bottom_values, initial_historical_top_values = get_all_hardness_values()

# Calculate initial limits for Bottom
initial_mean_bottom, initial_ucl_bottom, initial_lcl_bottom = calculate_control_limits(initial_historical_bottom_values)
if initial_ucl_bottom is None:
    initial_mean_bottom, initial_ucl_bottom, initial_lcl_bottom = DEFAULT_BOTTOM_MEAN, DEFAULT_BOTTOM_UCL, DEFAULT_BOTTOM_LCL
    print("Using default Bottom SPC limits on startup.")

# Calculate initial limits for Top
initial_mean_top, initial_ucl_top, initial_lcl_top = calculate_control_limits(initial_historical_top_values)
if initial_ucl_top is None:
    initial_mean_top, initial_ucl_top, initial_lcl_top = DEFAULT_TOP_MEAN, DEFAULT_TOP_UCL, DEFAULT_TOP_LCL
    print("Using default Top SPC limits on startup.")

# Pass empty lists for current readings on startup, as none have been entered yet
update_plot([], [],
            initial_mean_bottom, initial_ucl_bottom, initial_lcl_bottom,
            initial_mean_top, initial_ucl_top, initial_lcl_top)


# Start the Tkinter event loop
root.mainloop()
