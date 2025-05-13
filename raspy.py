from collections import defaultdict
import socket
import time
from time import sleep
import datetime
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from threading import Thread, Lock
from gpiozero import LED, Button, LEDBoard
import warnings
import os
from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.virtual import viewport
from luma.core.render import canvas
import threading
from matplotlib.animation import FuncAnimation
#from gpiozero import LED, LEDBoard
# GPIO Setup
button = Button(12)
yellow_led=LED(21)
# Network Config
UDP_PORT = 5005
UDP_SEND_PORT = 5006
node_red_ip="192.168.86.49"
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.bind(('', UDP_PORT))
updated_time=0
# Variables for data handling
esp_data = defaultdict(list)  # {IP: [sensor values]}
master_durations = defaultdict(int)  # {IP: total time as master}
master_switch_time = time.time()
current_master = None
log_file = None
start_time = time.time()
colors = ['blue', 'green', 'red']  # Colors for different master devices
current_color_index = 0

# Thread lock to ensure thread safety
lock = threading.Lock()

MATRIX_WIDTH = 8  # Width of one 1088AS module
MATRIX_HEIGHT = 8  # Height of the module
NUM_COLUMNS = 8    # Number of columns for ~30 seconds (30/4 = 7.5, rounded to 8)
data_index = 0

# Initialize the serial interface and the dot matrix
serial = spi(port=0, device=0, gpio=noop())
matrix = max7219(serial, cascaded=1, block_orientation=90, rotate=0)
matrix.contrast(16)  # Adjust brightness as needed

# Photocell data buffer (last 30 seconds), size 8 (for ~30 seconds with 4 second intervals)
photocell_data = [0] * 8  # List to store 8 values (one per 4-second window)
data_index = 0
segments = {
    'A': LED(5),
    'B': LED(6),
    'C': LED(13),
    'D': LED(19),
    'E': LED(26),
    'F': LED(24),
    'G': LED(25),
}
current_digits= None
stop_display = threading.Event()
# Define GPIO pins for digits (D1, D2, D3, D4)
digits = LEDBoard(17, 27, 22, 23)  # Control pins for each digit (Active LOW)

# Define digit patterns for numbers 0-9 (Active HIGH for common anode)
digit_patterns = [
    [1, 1, 1, 1, 1, 1, 0],  # 0
    [0, 1, 1, 0, 0, 0, 0],  # 1
    [1, 1, 0, 1, 1, 0, 1],  # 2
    [1, 1, 1, 1, 0, 0, 1],  # 3
    [0, 1, 1, 0, 0, 1, 1],  # 4
    [1, 0, 1, 1, 0, 1, 1],  # 5
    [1, 0, 1, 1, 1, 1, 1],  # 6
    [1, 1, 1, 0, 0, 0, 0],  # 7
    [1, 1, 1, 1, 1, 1, 1],  # 8
    [1, 1, 1, 1, 0, 1, 1],  # 9
]



# Reset ESPs and Start New Log
def reset_system():
    global log_file, start_time
    print("Resetting system...")
    #white_led.on()
    yellow_led.on()
    time.sleep(3)
    yellow_led.off()
    #white_led.off()

    # Close current log and start a new one
    if log_file:
        log_file.close()
    log_file = open(f"log_{time.strftime('%Y%m%d_%H%M%S')}.txt", "w")
    start_time = time.time()
    
    reset_message = "RESET"
    sock.sendto(reset_message.encode(), (node_red_ip, UDP_SEND_PORT))
    save_log_data()
# Button Listener
def handle_button_press():
    while True:
        button.wait_for_press()
        #reset_system()
        # Send RESET signal to all ESPs
        sock.sendto("RESET".encode(), ("255.255.255.255", UDP_PORT))
        reset_system()

# Process Incoming Data


# Update Photocell Data
def update_photocell_data(sensor_value):
    """Add a new photocell reading to the buffer, maintaining 8 positions for the last 30 seconds."""
    global photocell_data, start_time, updated_time  
    start_time=time.monotonic()
    # Shift the values down and add the new value at the start
    if (start_time-updated_time>4):
        photocell_data = [sensor_value] + photocell_data[:-1]  # Add new value at the start, shift the rest
        print(photocell_data)
        update_matrix()
        updated_time=start_time# Call to update the LED matrix
    #time.sleep(4)

# Matrix update function to show the photocell data on the LED matrix
def update_matrix():
    """Updates the LED matrix to show the photocell data trace."""
    with canvas(matrix) as draw:
        for row in range(8):  # Loop over the 8 rows of the matrix
            value = photocell_data[row]  # Get the value from the list corresponding to this row
            num_leds = min(value // 128, MATRIX_WIDTH)  # Scale the value to the number of LEDs in each row

            # Light up the appropriate number of LEDs in the row based on the scaled value
            for col in range(num_leds):
                draw.point((col, row), fill="white")  # Illuminate horizontally in the row

# Graph Update

# Save Log Data
def save_log_data():
    global esp_data, master_durations, current_master
    with lock:  # Ensure thread safety while accessing shared data
        if log_file:
            log_file.write(f"Master IP: {current_master}, Duration: {master_durations[current_master]}\n")
            for ip, readings in esp_data.items():
                log_file.write(f"{ip} Data: {readings}\n")
            log_file.flush()

# Main Function
def display_digits_thread():
    """Continuously updates the 7-segment display with the current master's IP last 3 digits."""
    global current_digits
    try:
        while not stop_display.is_set():  # Run until the stop signal is received
            if current_digits is not None:
                for pos in range(3):  # Cycle through each digit position
                    digit_num = int(current_digits[pos])  # Get the digit to display

                    # Set the segments for the current digit
                    for idx, state in enumerate(digit_patterns[digit_num]):
                        if state == 1:  # Segment ON (HIGH for common anode)
                            segments[list(segments.keys())[idx]].off()
                        else:  # Segment OFF (LOW for common anode)
                            segments[list(segments.keys())[idx]].on()

                    # Activate the current digit (Active LOW)
                    digits.off()  # Turn off all digits
                    digits[pos].on()  # Turn on the selected digit

                    sleep(0.005)  # Small delay for persistence of vision
    except Exception as e:
        print(f"Error in display_digits_thread: {e}")
    finally:
        # Clean up: turn off all segments and digits
        for led in segments.values():
            led.off()
        digits.off()

def process_data():
    """Processes incoming UDP data and updates the master IP and photocell readings."""
    global current_master, master_switch_time, current_digits
    while True:
        data, addr = sock.recvfrom(1024)  # Receive data from the socket
        message = data.decode()  # Decode the message
        ip = addr[0]  # Extract the sender's IP address

        if "MASTER" in message:
            sensor_value = int(message.split(',')[1])  # Extract sensor value
            update_photocell_data(sensor_value)  # Update the photocell data buffer
            print(sensor_value)

            with lock:  # Ensuring thread safety
                esp_data[ip].append((time.time(), sensor_value))
                #save_log_data()
                # Send sensor data via UDP to a different port
                udp_message = f"Sensor data from {ip}, {sensor_value}"
                sock.sendto(udp_message.encode(), (node_red_ip, UDP_SEND_PORT))  
                print(udp_message)
                if current_master != ip:  # If there's a master change
                    if current_master:
                        master_durations[current_master] += time.time() - master_switch_time

                    current_master = ip  # Update the current master
                    print(current_master)
                    print("**********************************************************")
                    master_switch_time = time.time()

                    # Extract the last 3 digits from the IP address
                    last_segment = current_master.split('.')[-2]
                    print("last segment:")
                    print(last_segment)
                    last_segment1 = current_master.split('.')[-1]
                    print("last segment 1:")
                    print(last_segment1)
                    #current_digits = (last_segment[1:] + last_segment1).zfill(3)[:3]
                    #current_digits = (last_segment[1:] + last_segment1)
                    current_digits = (last_segment1)
                    print(f"New master: {current_master} (digits: {current_digits})")

# Main Function
def main():
    # Start threads
    threading.Thread(target=handle_button_press, daemon=True).start()
    threading.Thread(target=process_data, daemon=True).start()

    # Start the 7-segment display thread
    display_thread = threading.Thread(target=display_digits_thread, daemon=True)
    display_thread.start()

    # Start the live graph
    

if __name__ == "__main__":  
    reset_system()  # Initialize system
    main()

