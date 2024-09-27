import subprocess
import time
import os
import platform
from collections import defaultdict, deque
from colorama import init, Fore, Style
from tabulate import tabulate

# Initialize Colorama
init()

OUI_FILE = 'manuf'  # The downloaded Wireshark OUI file name
MAX_HISTORY = 10    # Maximum number of historical points to track for RSSI

# Dictionary to store historical RSSI values
rssi_history = defaultdict(lambda: deque(maxlen=MAX_HISTORY))

def load_oui_database(oui_file):
    """Load the OUI database from the given file into a dictionary."""
    oui_dict = {}
    try:
        with open(oui_file, 'r') as file:
            for line in file:
                # Skip comments and empty lines
                if line.startswith('#') or not line.strip():
                    continue

                # Split the line by whitespace
                parts = line.split()
                if len(parts) >= 3:
                    mac_prefix = parts[0].strip()  # MAC address prefix
                    short_name = parts[1].strip()   # Shortened name (not used here)
                    manufacturer = ' '.join(parts[2:]).strip()  # Full manufacturer name
                    oui_dict[mac_prefix] = manufacturer
        print(f"Loaded {len(oui_dict)} entries from OUI database.")
    except Exception as e:
        print(f"Error loading OUI database: {e}")
    return oui_dict

def get_manufacturer(mac, oui_dict):
    """Fetch the manufacturer information based on MAC address using a local OUI database."""
    # Normalize the MAC address and get the first three bytes
    mac_prefix = ':'.join(mac.split(':')[:3]).upper()  # Get the first three bytes of the MAC address
    return oui_dict.get(mac_prefix, 'Unknown Manufacturer')

def get_color_for_signal(signal):
    """Return color based on signal strength."""
    if signal > 70:
        return Fore.GREEN  # Strong Signal
    elif signal > 50:
        return Fore.YELLOW  # Good Signal
    elif signal > 30:
        return Fore.LIGHTYELLOW_EX  # Fair Signal
    else:
        return Fore.RED  # Weak Signal

def get_colored_block(signal):
    """Return a colored block based on signal strength."""
    color = get_color_for_signal(signal)
    return f"{color}█{Style.RESET_ALL}" if signal > 0 else " "

def generate_signal_graph(rssi_values):
    """Generate a simple ASCII graph for signal strength history with colors."""
    if not rssi_values:
        return " " * MAX_HISTORY  # Empty history graph

    graph = ""
    for value in rssi_values:
        graph += get_colored_block(value)

    return graph

def list_and_sort_wifi_networks_linux(oui_dict):
    """List and sort Wi-Fi networks for Linux using nmcli."""
    try:
        result = subprocess.run(['nmcli', '-f', 'SSID,BSSID,SIGNAL,CHAN', 'dev', 'wifi'], capture_output=True, text=True)
        
        if result.returncode == 0:
            output = result.stdout.splitlines()
            networks = []
            for line in output[1:]:
                if line.strip():
                    parts = [p.strip() for p in line.split() if p]
                    if len(parts) >= 4:
                        ssid = parts[0]
                        bssid = parts[1]
                        try:
                            signal = int(parts[2])
                        except ValueError:
                            signal = 0
                        channel = parts[3]
                        networks.append({'SSID': ssid, 'BSSID': bssid, 'SIGNAL': signal, 'CHANNEL': channel})

            return sorted(networks, key=lambda x: x['SIGNAL'], reverse=True)

    except Exception as e:
        print(f"An error occurred: {e}")
    return []

def list_and_sort_wifi_networks_macos(oui_dict):
    """List and sort Wi-Fi networks for macOS using airport."""
    try:
        result = subprocess.run(['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport', '-s'], capture_output=True, text=True)
        
        if result.returncode == 0:
            output = result.stdout.splitlines()
            networks = []
            for line in output[1:]:
                if line.strip():
                    parts = line.split()
                    ssid = parts[0]
                    bssid = parts[1]
                    signal = int(parts[2])
                    channel = parts[3] if len(parts) > 3 else 'N/A'
                    networks.append({'SSID': ssid, 'BSSID': bssid, 'SIGNAL': signal, 'CHANNEL': channel})

            return sorted(networks, key=lambda x: x['SIGNAL'], reverse=True)

    except Exception as e:
        print(f"An error occurred: {e}")
    return []

def list_and_sort_wifi_networks_windows(oui_dict):
    """List and sort Wi-Fi networks for Windows using netsh."""
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'network'], capture_output=True, text=True)

        if result.returncode == 0:
            output = result.stdout.splitlines()
            networks = []
            ssid, bssid, signal, channel = None, None, None, None
            
            for line in output:
                line = line.strip()
                if line.startswith("SSID"):
                    ssid = line.split(":")[1].strip()
                elif line.startswith("BSSID"):
                    bssid = line.split(":")[1].strip()
                elif line.startswith("Signal"):
                    signal = int(line.split(":")[1].strip().replace('%', ''))
                elif line.startswith("Channel"):
                    channel = line.split(":")[1].strip()
                    networks.append({'SSID': ssid, 'BSSID': bssid, 'SIGNAL': signal, 'CHANNEL': channel})

            return sorted(networks, key=lambda x: x['SIGNAL'], reverse=True)

    except Exception as e:
        print(f"An error occurred: {e}")
    return []

def list_and_sort_wifi_networks(oui_dict):
    """Detect the operating system and list Wi-Fi networks accordingly."""
    system = platform.system()
    
    if system == "Linux":
        return list_and_sort_wifi_networks_linux(oui_dict)
    elif system == "Darwin":  # macOS
        return list_and_sort_wifi_networks_macos(oui_dict)
    elif system == "Windows":
        return list_and_sort_wifi_networks_windows(oui_dict)
    else:
        print("Unsupported operating system.")
        return []

def display_wifi_networks(oui_dict):
    """Display the detected Wi-Fi networks in a formatted table."""
    networks = list_and_sort_wifi_networks(oui_dict)
    
    # Prepare the table data
    table_data = []
    for index, network in enumerate(networks):
        manufacturer = get_manufacturer(network['BSSID'], oui_dict)
        color = get_color_for_signal(network['SIGNAL'])
        colored_signal = f"{color}{network['SIGNAL']}%{Style.RESET_ALL}"
        
        # Update the historical RSSI data
        rssi_history[network['BSSID']].append(network['SIGNAL'])
        
        # Generate the signal history graph
        signal_graph = generate_signal_graph(rssi_history[network['BSSID']])
        
        # Append data to table
        table_data.append([index + 1, network['SSID'], network['BSSID'], colored_signal, network['CHANNEL'], manufacturer, signal_graph])

    # Define the table headers
    headers = ['No.', 'SSID', 'BSSID', 'Signal Strength', 'Channel', 'Manufacturer', 'RSSI History']
    
    # Clear the screen before printing
    os.system('clear' if os.name == 'posix' else 'cls')

    # Print the table using tabulate
    print(tabulate(table_data, headers=headers, tablefmt='fancy_grid'))

# Load the OUI database from the local file
oui_dict = load_oui_database(OUI_FILE)

# Continuously refresh the network list
try:
    while True:
        display_wifi_networks(oui_dict)
        time.sleep(5)  # Update interval in seconds
except KeyboardInterrupt:
    print("\nExiting...")
