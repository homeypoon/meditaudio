# meditaudio

This program records EEG data and computes the associated band powers (Alpha, Beta, Theta, Delta) in real-time. The data is saved in a CSV file, which includes the following:

- **Timestamp**: The time the data was recorded.
- **TP9, AF7, AF8, TP10, Right AUX**: EEG channel values.
- **Alpha, Beta, Theta, Delta**: EEG frequency bands.

## Setup

### Prerequisites

Before running the program, ensure you have the following setup:

1. **MuseLSL**: The software used to stream data from your Muse EEG device.
2. **Python**: Ensure Python 3 is installed on your system.

### Steps to Run

#### 1. Start the MuseLSL Stream

- Open a terminal window and start the MuseLSL streaming process:

  ```bash
  muselsl stream
  ```

  This will initiate the connection to the Muse EEG device and start streaming the data.

#### 2. Run the Python Script to Record Data

- Open a **separate terminal window** and run the following Python command to start recording the EEG data:

  ```bash
  python3 recordData.py
  ```

  OR

  ```bash
  python recordData.py
  ```

  This will begin the real-time data recording and save the results in a CSV file.

#### 3. CSV File Output

- The data will be saved in a CSV file named `eeg_data_TIMESTAMP.csv`, where `TIMESTAMP` is the time the script was started (in the format `YYYYMMDD_HHMMSS`).

  Example: `eeg_data_20230510_143200.csv`

---

## File Structure

The CSV file contains the following columns:

- **Timestamp**: ISO 8601 timestamp when the data was recorded.
- **TP9, AF7, AF8, TP10, Right AUX**: The raw EEG signal data from the respective channels.
- **Alpha, Beta, Theta, Delta**: The band power values for each frequency range.

---

## Credit

This program uses the MuseLSL library for EEG data streaming. Special thanks to Alexandre Barachant for developing Muse-LSL, which provides the connection to Muse EEG devices for lab streaming.

[Click here to visit MuseLSL on GitHub](https://github.com/alexandrebarachant/muse-lsl)
