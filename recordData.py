# -*- coding: utf-8 -*-
"""
Estimate Relaxation from Band Powers

This example shows how to buffer, epoch, and transform EEG data from a single
electrode into values for each of the classic frequencies (e.g. alpha, beta, theta)
Furthermore, it shows how ratios of the band powers can be used to estimate
mental state for neurofeedback.

The neurofeedback protocols described here are inspired by
*Neurofeedback: A Comprehensive Review on System Design, Methodology and Clinical Applications* by Marzbani et. al

Adapted from https://github.com/NeuroTechX/bci-workshop
"""

import numpy as np  # Module that simplifies computations on matrices
import matplotlib.pyplot as plt  # Module used for plotting
from pylsl import StreamInlet, resolve_byprop  # Module to receive EEG data
import utils

import csv
import os
from datetime import datetime
from time import time, sleep


# Handy little enum to make code more readable
class Band:
    Delta = 0
    Theta = 1
    Alpha = 2
    Beta = 3


""" EXPERIMENTAL PARAMETERS """
# Modify these to change aspects of the signal processing

# This buffer will hold last n seconds of data and be used for calculations
BUFFER_LENGTH = 15

# Length of the epochs used to compute the FFT (in seconds)
EPOCH_LENGTH = 2

# Amount of overlap between two consecutive epochs (in seconds)
OVERLAP_LENGTH = 1

# Amount to 'shift' the start of each next consecutive epoch
SHIFT_LENGTH = EPOCH_LENGTH - OVERLAP_LENGTH

# Index of the channel(s) (electrodes) to be used
# 0 = left ear, 1 = left forehead, 2 = right forehead, 3 = right ear
INDEX_CHANNEL = [0]

# Timeout for stream resolution
LSL_SCAN_TIMEOUT = 5


def reconnect_stream(timeout=LSL_SCAN_TIMEOUT):
    """
    Reconnect to the EEG stream if disconnected
    """
    while True:
        try:
            print('Attempting to reconnect to EEG stream...')
            streams = resolve_byprop('type', 'EEG', timeout=timeout)
            if len(streams) == 0:
                print('Can\'t find EEG stream. Retrying in 5 seconds...')
                sleep(5)
                continue

            # Set active EEG stream to inlet and apply time correction
            print("Reconnected. Resuming data acquisition...")
            inlet = StreamInlet(streams[0], max_chunklen=12)
            eeg_time_correction = inlet.time_correction()

            # Get the stream info
            info = inlet.info()
            fs = int(info.nominal_srate())

            return inlet, fs, eeg_time_correction

        except Exception as e:
            print(f'Error during reconnection: {e}')
            print('Retrying in 5 seconds...')
            sleep(5)


if __name__ == "__main__":

    """ 1. CONNECT TO EEG STREAM """

    # Search for active LSL streams
    print('Looking for an EEG stream...')
    streams = resolve_byprop('type', 'EEG', timeout=LSL_SCAN_TIMEOUT)
    if len(streams) == 0:
        raise RuntimeError('Can\'t find EEG stream.')

    # Set active EEG stream to inlet and apply time correction
    print("Start acquiring data")
    inlet = StreamInlet(streams[0], max_chunklen=12)
    eeg_time_correction = inlet.time_correction()

    # Get the stream info and description
    info = inlet.info()
    description = info.desc()

    # Get the sampling frequency
    # This is an important value that represents how many EEG data points are
    # collected in a second. This influences our frequency band calculation.
    # for the Muse 2016, this should always be 256
    fs = int(info.nominal_srate())

    """ 2. INITIALIZE BUFFERS """

    # Initialize raw EEG data buffer
    eeg_buffer = np.zeros((int(fs * BUFFER_LENGTH), 1))
    filter_state = None  # for use with the notch filter

    # Compute the number of epochs in "buffer_length"
    n_win_test = int(np.floor((BUFFER_LENGTH - EPOCH_LENGTH) /
                              SHIFT_LENGTH + 1))

    # Initialize the band power buffer (for plotting)
    # bands will be ordered: [delta, theta, alpha, beta]
    band_buffer = np.zeros((n_win_test, 4))

    """ 3. GET DATA """

    # The try/except structure allows to quit the while loop by aborting the
    # script with <Ctrl-C>
    print('Press Ctrl-C in the console to break the while loop.')

    # Create folder to store CSVs
    folder_name = "eeg_data"
    os.makedirs(folder_name, exist_ok=True)

    # Generate dynamic filename with timestamp
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = os.path.join(folder_name, f'eeg_data_{timestamp_str}.csv')

    # Write header to the new CSV file
    with open(csv_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp', 'TP9', 'AF7', 'AF8', 'TP10',
                        'Right AUX', 'Alpha', 'Beta', 'Theta', 'Delta'])

    last_update = time()

    try:
        while True:
            """ 3.1 ACQUIRE DATA """
            try:
                # Obtain EEG data from the LSL stream
                eeg_data, timestamp = inlet.pull_chunk(
                    timeout=1, max_samples=int(SHIFT_LENGTH * fs))

                # Update last successful data reception time
                if len(eeg_data) > 0:
                    last_update = time()

            except Exception as e:
                print(f'Lost connection to stream: {e}')
                # Attempt to reconnect
                inlet, fs, eeg_time_correction = reconnect_stream()
                # Reinitialize buffers after reconnection if necessary
                continue

            # Check if we haven't received data for too long
            if time() - last_update > 10:
                print('No data received for 10 seconds. Attempting to reconnect...')
                inlet, fs, eeg_time_correction = reconnect_stream()
                last_update = time()
                continue

            # Check if we received data
            if len(eeg_data) == 0:
                continue  # Skip if no data received

            # Convert to NumPy array
            eeg_array = np.array(eeg_data)

            # Get all channels for raw data storage
            if eeg_array.shape[1] >= 5:
                # Last sample, first 5 channels
                latest_channels = eeg_array[-1, :5]
            else:
                # Use whatever channels are available
                latest_channels = eeg_array[-1]

            # Extract only the channel of interest for analysis
            ch_data = eeg_array[:, INDEX_CHANNEL]

            # Update EEG buffer with the new data (only once!)
            eeg_buffer, filter_state = utils.update_buffer(
                eeg_buffer, ch_data, notch=True,
                filter_state=filter_state)

            """ 3.2 COMPUTE BAND POWERS """
            # Get newest samples from the buffer
            data_epoch = utils.get_last_data(eeg_buffer,
                                             EPOCH_LENGTH * fs)

            # Compute band powers
            band_powers = utils.compute_band_powers(data_epoch, fs)
            band_buffer, _ = utils.update_buffer(band_buffer,
                                                 np.asarray([band_powers]))

            # Compute the average band powers for all epochs in buffer
            smooth_band_powers = np.mean(band_buffer, axis=0)

            """ 3.3 COMPUTE NEUROFEEDBACK METRICS """
            # Alpha Protocol
            alpha_metric = smooth_band_powers[Band.Alpha] / \
                smooth_band_powers[Band.Delta]

            # Beta Protocol
            beta_metric = smooth_band_powers[Band.Beta]

            # Alpha/Theta Protocol
            theta_metric = smooth_band_powers[Band.Theta] / \
                smooth_band_powers[Band.Alpha]

            """ 3.4 SAVE DATA """
            # Save all data to CSV
            with open(csv_file, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    *latest_channels,  # TP9, AF7, AF8, TP10, Right AUX
                    smooth_band_powers[Band.Alpha],
                    smooth_band_powers[Band.Beta],
                    smooth_band_powers[Band.Theta],
                    smooth_band_powers[Band.Delta]
                ])

    except KeyboardInterrupt:
        print('Closing!')
        print(f'Data saved to: {csv_file}')
