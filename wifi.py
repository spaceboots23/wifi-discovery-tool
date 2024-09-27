import subprocess
from colorama import init, Fore, Style

# Initialize Colorama
init()

OUI_FILE = 'manuf'  # The downloaded Wireshark OUI file name

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
    else:
        return Fore.RED  # Weak Signal

def list_and_sort_wifi_networks_linux(oui_dict):
    try:
        # Run the 'nmcli' command to get SSID, BSSID, and signal strength (RSSI)
        result = subprocess.run(['nmcli', '-f', 'SSID,BSSID,SIGNAL', 'dev', 'wifi'], capture_output=True, text=True)
        
        if result.returncode == 0:
            output = result.stdout.splitlines()
            
            # Skip the header and parse the rest
            networks = []
            for line in output[1:]:
                if line.strip():  # Ignore empty lines
                    # Split the line into columns and handle missing data
                    parts = [p.strip() for p in line.split() if p]
                    if len(parts) >= 3:
                        ssid = parts[0]
                        bssid = parts[1]
                        try:
                            signal = int(parts[2])
                        except ValueError:
                            signal = 0  # Default to 0 if conversion fails
                        networks.append({'SSID': ssid, 'BSSID': bssid, 'SIGNAL': signal})

            # Sort networks by RSSI (signal strength)
            sorted_networks = sorted(networks, key=lambda x: x['SIGNAL'], reverse=True)
            
            print("Available Wi-Fi Networks (sorted by RSSI):")
            for index, network in enumerate(sorted_networks):
                manufacturer = get_manufacturer(network['BSSID'], oui_dict)
                color = get_color_for_signal(network['SIGNAL'])  # Get color based on signal strength
                print(f"{color}{index + 1}. SSID: {network['SSID']}, RSSI: {network['SIGNAL']}%, BSSID: {network['BSSID']}, Manufacturer: {manufacturer}{Style.RESET_ALL}")
        else:
            print(f"Failed to run command: {result.stderr}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Load the OUI database from the local file
oui_dict = load_oui_database(OUI_FILE)

# Run the function with the loaded OUI database
list_and_sort_wifi_networks_linux(oui_dict)
