# ************ FS20F_02_SAT ************
#
# PURPOSE:
# python script outputting O2 saturation from device FS20F
#
# AUTHOR:
# Kyle Mulholland
#
# ************************


# ************ IMPORTS ************
import subprocess
import pexpect
import time



# ************ FUNCTIONS ************

# Error handling for EXPECT calls
def ChildExpectError(i):
    if i == 1:
        print("pexpect.EOF")
    elif i == 2:
        print("Call timed out.")
    exit()



# ************ VARIABLES ************
DEVICE =  "F0:45:DA:06:96:9D"   # Device ID
pexpect_short_timeout = 10      # Time (sec) for pexpect to return
pexpect_long_timeout = 60      # Time (sec) for pexpect to return



# ************ MAIN ************

# Activate gatttool
child = pexpect.spawn(f"gatttool -t random --interactive")
index = child.expect(["", pexpect.EOF, pexpect.TIMEOUT], timeout=pexpect_short_timeout)
if index > 0:
    ChildExpectError(index)
            
# Connect to device
print(f"Attempting to connect to {DEVICE}...")
child.sendline(f"connect {DEVICE}")
index = child.expect(["Connection successful", pexpect.EOF, pexpect.TIMEOUT], timeout=pexpect_long_timeout)
if index > 0:
    ChildExpectError(index)
print("Connected!")

# Check battery level
child.sendline("char-read-hnd 0a")
index = child.expect(["Characteristic value/descriptor: ", pexpect.EOF, pexpect.TIMEOUT], timeout=pexpect_short_timeout)
if index > 0:
    ChildExpectError(index)
child.expect("\n", timeout=pexpect_short_timeout)

battery_byte = child.before.strip().decode("utf-8")
battery_val = float.fromhex(battery_byte)
print(f'Battery level: {battery_val}%')

# Set data flags
spo2_data_available = False
waveform_data_available = False


while True:

    index = child.expect(["Notification handle = 0x000e value: ", pexpect.EOF, pexpect.TIMEOUT], timeout=pexpect_short_timeout)
    if index > 0:
        ChildExpectError(index)
    packet_rx_time = time.time()*10**9  # nsec
    
    # Measurement specific data command:
    # fe - Protocol header    # 08 - Bag length    # 56 - measurement specific data command
    child.expect("fe 08 56", timeout=pexpect_short_timeout)
    child.expect("\n", timeout=3)
    raw_data_str = child.before.strip().decode("utf-8")
    #print(f'{len(raw_data_str.split())}\t{raw_data_str.split()}')

    # Pulse wave only data packet (if required)
    for i in range(len(raw_data_str.split())):
        
        # Pulse waveform (PPI/PPG??) - Values 0-100
        if i==0:
            pulse_waveform = float.fromhex(raw_data_str.split()[0])

            waveform_data_available = True
        

        # Heart rate
        if i==9:
            #Check for invalid pulse (01ff = 511)
            if (raw_data_str.split()[8]=='01' and raw_data_str.split()[9]=='ff'):
                print('*** WARNING: HR SIGNAL LOST - Check contact between sensor and finger ***')
                hr = float('NaN')
            else:
                hr = float.fromhex(raw_data_str.split()[8] + raw_data_str.split()[9])   
            
            spo2_data_available = True
            #print(f'HR = {hr} bpm')
        
        # SPO2 (oxygen saturation)
        if i == 10:

            # Check for invalid SPO2 (7f = 127)
            if (raw_data_str.split()[10]=='7f'):
                print('*** WARNING: SPO2 SIGNAL LOST - Check contact between sensor and finger ***')
                spo2 = float('NaN')
            else:
                spo2 = float.fromhex(raw_data_str.split()[10])
            
            spo2_data_available = True 
            #print(f'SPO2 = {spo2} %')

        # PI (perfusion index) - Perfusion index is an indication of the pulse strength at the sensor site. The PI's values range from 0.02% for very weak pulse to 20% for extremely strong pulse. 
        # https://www.masimo.co.uk/siteassets/uk/documents/pdf/clinical-evidence/whitepapers/lab3410f_whitepapers_perfusion_index.pdf
        if i == 12:
            pi = (float.fromhex(raw_data_str.split()[11] + raw_data_str.split()[12]))/1000.0
            spo2_data_available = True
            #print(f'PI = {pi}')


        
    # Display output data
    #print(f'Output: ({raw_data_str}) at Time: {packet_rx_time}')
    if (spo2_data_available==True):
        print(f'SPO2: {spo2} %\tHR: {hr} bpm\tPI: {pi} %\t\tTime: {packet_rx_time} nsec')
        
        spo2_data_available = False
    
    # if (waveform_data_available==True):
    #     print(f'PPI_val: {pulse_waveform}\t\tTime: {packet_rx_time} nsec')
        
    #     waveform_data_available = False
    # print('\n')


