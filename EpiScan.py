#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 31 13:20:04 2023
@author: KaliPhobos
"""
import datetime
import math
import numpy
from PyQt6 import QtWidgets, uic
import sys
import cv2
import os
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Initialize all vars
silent_noGui = False

"""
Table 'self.brightness' contains the raw self.brightness values split into 5 lines:
1. line (0): The absolute self.brightness for each frame
2. line (1): The perceived self.brightness for each frame (thx D. Finley, alienryderflex.com/hsp.html)
3. line (2): The R-channels self.brightness for each frame
4. line (3): The G-channels self.brightness for each frame
5. line (4): The B-channels self.brightness for each frame
Table 'self.brightness_absolute' contains statistics across X lines, X being the max span according to settings
1. line (0): The absolute self.brightness changes across 2 neighboring frames (starting with the first)
2. line (1): The absolute self.brightness changes across 3 neighboring frames (starting with the first)
3. line (2): The absolute self.brightness changes across 4 neighboring frames (starting with the first) and so on
Table 'self.brightness_perceived' does the same but uses the perceived instead of actual self.brightness as base data
Table 'self.brightness_channel_R' does the same but uses the R-channel only as base data
Table 'self.brightness_channel_G' does the same but uses the R-channel only as base data
Table 'self.brightness_channel_B' does the same but uses the R-channel only as base data
"""
class MainWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        # Initialize all vars
        self.type = 0  # The currently selected method how brightness should be handled (1...3 are valid)
        self.type_1 = "Absolute brightness"  # String for method 1
        self.type_2 = "Perceived brightness"  # String for method 2
        self.type_3 = "R,G,B as separate channels"  # String for method 3
        self.fps = 0
        self.file_path = ''  # Path to the video file
        self.file_path_old = ''  # Path to the previously processed video file
        self.gui_isResetForced = True  # Should all cached data be deleted instead of reused?
        self.brightness = numpy.zeros((5, 2))  # The array containing all resulting raw data
        self.brightness_absolute = numpy.zeros((2, 2))
        self.brightness_perceived = numpy.zeros((2, 2))
        self.brightness_channel_R = numpy.zeros((2, 2))
        self.brightness_channel_G = numpy.zeros((2, 2))
        self.brightness_channel_B = numpy.zeros((2, 2))
        self.is_analyzed = [False, False, False]  # Was an analysis already completed? (Array of booleans)
        self.cap = None  # Contains all frames
        self.gui_frameSpan = 20  # Current width of the analysis span
        self.gui_plotMaxColors = 20  # Number of plots to be drawn if the analysis span exceeds 10
        self.gui_colorBorderValue = 0.8  # Value (0...1) at which the second color should be placed in the linear gradient
        self.gui_color1 = '#FF7000'  # Color 1 for 3-color linear gradient coloring of data plots
        self.gui_color2 = '#FF0000'  # Color 2 for 3-color linear gradient coloring of data plots
        self.gui_color4 = '#000000'  # Color 3 for 3-color linear gradient coloring of data plots
        self.gui_yLim = 120  # Maximum Y-Value for plots
        self.timestamp_start = datetime.datetime

        uic.loadUi("EpiScan_GUI.ui", self)
        self.button_load.clicked.connect(self.gui_load_file)
        self.button_applyGraphics.clicked.connect(self.gui_apply_graphics_changes)
        self.button_applySettings.clicked.connect(self.gui_apply_settings_changes)
        self.button_processFile.clicked.connect(self.gui_forced_processFile)
        self.button_processData.clicked.connect(self.gui_forced_processData) # Re-process all collected data on video file (forced)
        self.button_drawGraph.clicked.connect(self.gui_forced_displayGraph) # Re-draw graph using given results (forced)

    def gui_forced_processFile(self):
        if os.path.isdir(self.file_path):
            print("Please select a file, not a folder")
            return
        if os.path.isfile(self.file_path):
            print("Provided file: " + str(self.file_path))
        else:
            print("Please select a file")
            return
        if (self.file_path == self.file_path_old):
            print("Duplicate file... Click again to ignore & analyze")
            self.file_path_old = ""
            return
        self.file_path_old = self.file_path
        self.button_load.setText("Abort")
        self.processFile()

    def gui_forced_processData(self):
        self.processData()

    def gui_forced_displayGraph(self):
        self.displayGraph()

    def gui_load_file(self):
        # Read the new file path and forward it
        self.file_path = self.lineEdit_filePath.text()
        self.gui_forced_processFile()



    # Apply changes in GUI controls so they can be considered
    def gui_apply_settings_changes(self):
        print("APPLY SETTINGS CHANGES!")
        # Apply changes in GUI
        self.gui_frameSpan = self.spinBox_frameSpan.value()
        print("Set: gui_frameSpan = " + str(self.gui_frameSpan))
        self.gui_isResetForced = self.checkBox_isResetForced.isChecked()
        print("Set: gui_isResetForced = " + str(self.gui_isResetForced))
        self.gui_plotMaxColors = self.spinBox_plotMaxColors.value()
        print("Set: gui_plotMaxColors = " + str(self.gui_plotMaxColors))


    def gui_apply_graphics_changes(self):
        print("APPLY GRAPHICS CHANGES!")
        # Apply changes in GUI

        self.gui_colorBorderValue = self.doubleSpinBox_colorBorderValue.value()
        print("Set: gui_colorBorderValue = " + str(self.gui_colorBorderValue))
        self.gui_color1 = self.lineEdit_color1.text()
        print("Set: gui_color1 = " + str(self.gui_color1))
        self.gui_color2 = self.lineEdit_color2.text()
        print("Set: gui_color2 = " + str(self.gui_color2))
        self.gui_color4 = self.lineEdit_color3.text()
        print("Set: gui_color4 = " + str(self.gui_color4))
        self.gui_yLim = self.spinBox_yLim.value()
        print("Set: gui_yLim = " + str(self.gui_yLim))

    def processFile(self): # Read the contents of a given video file and analyze each frame
        # Load the video and determine number of frames and self.fps
        print("Load File " + str(self.file_path))
        self.cap = cv2.VideoCapture(self.file_path)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))

        # Check if the file has been analyzed before and a .csv file with the results is available
        if (os.path.isfile(self.file_path+".csv")):
            # Load the data from the CSV file
            self.brightness = numpy.loadtxt(self.file_path + ".csv", delimiter=',')
            print("File " + self.file_path + ".csv found, restoring data...")
        else:
            print("No file '" + self.file_path + ".csv' with cached data found. Will have to analyze file")

            # Check if a new file has been selected, so old data has to be purged
            if (self.file_path_old != self.file_path or self.gui_isResetForced or self.cap == None or len(self.brightness[0]) != int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))):
                self.brightness = numpy.zeros((5, self.frame_count))
                self.brightness_absolute = numpy.zeros((self.gui_frameSpan, self.frame_count))
                self.brightness_perceived = numpy.zeros((self.gui_frameSpan, self.frame_count))
                self.brightness_channel_R = numpy.zeros((self.gui_frameSpan, self.frame_count))
                self.brightness_channel_G = numpy.zeros((self.gui_frameSpan, self.frame_count))
                self.brightness_channel_B = numpy.zeros((self.gui_frameSpan, self.frame_count))
                self.is_analyzed = [False, False, False]


            # Determine the selected self.brightness option
            self.brightness_type = self.comboBox_brightness.currentText()
            print("Trying to match analysis mode '" + str(self.brightness_type) + '\'')
            print("Available options: ")
            print("1: '" + str(self.type_1) + '\'')
            print("2: '" + str(self.type_2) + '\'')
            print("3: '" + str(self.type_3) + '\'')
            match self.brightness_type:
                case str(self.type_1):
                    self.type = 1
                    print("Analysis on " + str(self.type_1))
                    self.det_brightness_absolute()
                case str(self.type_2):
                    self.type = 2
                    print("Analysis on " + str(self.type_2))
                    self.det_brightness_perceived()
                case str(self.type_2):
                    self.type = 3
                    print("Analysis on " + str(self.type_3))
                    self.det_brightness_separate()
                case _:
                    print("ERROR: Unknown analysis mode selected: " + str(self.type))
                    return

            # Step 1 completed, data from all frames has been collected
            self.reportStatus("Step 1/2 completed, pushing data to file...", self.frame_count, self.frame_count)

            # Save the self.brightness array to a CSV file
            print("Saving data to: " + self.file_path+'.csv')
            numpy.savetxt(self.file_path+'.csv', self.brightness, delimiter=',')

        self.button_load.setText("LOAD")
        # Process pending events to update the GUI
        QtWidgets.QApplication.processEvents()
        self.processData()


    def processData(self):

        # Check if cached data is supposed to be deleted & create new arrays if necessary
        # TODO: How to handle cases in which only gui_maxSpan is getting increased? Cached data should then be used but new data added
        if (self.file_path_old != self.file_path or self.gui_isResetForced or self.cap == None or len(self.brightness[0]) != int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))):
            print("set brightness data arrays to appropriate size")
            self.brightness_absolute = numpy.zeros((self.gui_frameSpan, self.frame_count))
            self.brightness_perceived = numpy.zeros((self.gui_frameSpan, self.frame_count))
            self.brightness_channel_R = numpy.zeros((self.gui_frameSpan, self.frame_count))
            self.brightness_channel_G = numpy.zeros((self.gui_frameSpan, self.frame_count))
            self.brightness_channel_B = numpy.zeros((self.gui_frameSpan, self.frame_count))
            self.is_analyzed = [False, False, False]
        else:
            print("cached data looks good, will not be deleted")

        if (self.type == 1 and len(self.brightness_absolute) < self.gui_frameSpan):
            print("additional lines required as gui_maxSpan was increased")

        for i in range(0, len(self.is_analyzed)):
            print("DEBUG: is_analyzed[" + str(i) + "] is " + str(self.is_analyzed[i]))

        # Check if processing is even necessary
        if (self.cap == None):
            print("No video file has been selected. Returning.")
            return

        print("self.brightness_absolute is of size " + str(len(self.brightness_absolute)) + "x" + str(len(self.brightness_absolute[0])))

        if (self.is_analyzed[self.type - 1] == True):
            # Report current status
            print("Cached data found, no new analysis necessary.")
            self.reportStatus("Step 2/2 (processing CACHED data)", len(self.brightness[0]), len(self.brightness[0]))
            QtWidgets.QApplication.processEvents()
            # Display graph from cached data, then return
            self.displayGraph()
            return

        # Report current status
        self.reportStatus("Step 2/2 (analyzing data) begins...", 0)
        QtWidgets.QApplication.processEvents()

        # Create separate statistics for each frame span
        print("DEBUG: Frame spans in which brightness changes will be calculated) are 2..." + str(self.gui_frameSpan) + " (max value, 'frame_span')")
        for frame_span in range(1, self.gui_frameSpan):
            # Iterate over all video frames (except the last X frames, X being the current frame span)
            print("DEBUG: span=" + str(frame_span) + ", iterating over frames 0..." + str(self.frame_count - frame_span - 1) + " (will decrease as span size is going up)")
            for i in range(0, self.frame_count - frame_span):
                # Absolute self.brightness analysis
                if (self.type == 1):
                    value = 0
                    # print("DEBUG: j is " + str(i) + "..." + str(i + frame_span))
                    for j in range(i, i + frame_span):
                        # Sum up changes across the current frame span
                        value += abs(self.brightness[self.type - 1, j] - self.brightness[self.type - 1, j + 1])
                    self.brightness_absolute[frame_span - 1][i] = value / (0.7 * frame_span)

                # Perceived self.brightness analysis
                elif (self.type == 2):
                    value = 0
                    for j in range(i, i + frame_span):
                        # Sum up changes across the current frame span
                        value += abs(self.brightness[self.type - 1, j] - self.brightness[self.type - 1, j + 1])
                    self.brightness_perceived[frame_span - 1][i] = value

                # Separate analysis for each channel
                elif (self.type == 3):
                    value = [0, 0, 0]
                    for j in range(i, i + frame_span):
                        # Sum up changes across the current frame span
                        value[0] += abs(self.brightness[self.type - 1, j] - self.brightness[self.type - 1, j + 1])
                        value[1] += abs(self.brightness[self.type, j] - self.brightness[self.type, j + 1])
                        value[2] += abs(self.brightness[self.type + 1, j] - self.brightness[self.type + 1, j + 1])
                    self.brightness_channel_R[frame_span - 1][i] = value[0]
                    self.brightness_channel_R[frame_span - 1][i] = value[1]
                    self.brightness_channel_R[frame_span - 1][i] = value[2]

                else:
                    print("ERROR: Unknown analysis mode selected: " + str(self.type))
                    return

                # Update GUI to track progress
                if (i % 10000 == 0):
                    self.reportStatus("Step 2/2 (analyzing data)", self.frame_count * frame_span + i, self.gui_frameSpan * (self.frame_count - self.gui_frameSpan / 2))
                    # TODO: Numbers appear to be wrong, reached values >>100%
                    # Process pending events to update the GUI
                    QtWidgets.QApplication.processEvents()

                    if (i == 100000):
                        global timestamp_start
                        print("100'000 units processed, calculating ETA")
                        # timestamp_current = datetime.datetime
                        # timestamp_delta = datetime.timedelta(timestamp_current-timestamp_delta)
                        # print(str(timestamp_delta))

        self.reportStatus("Step 2/2 (analyzing data)", self.frame_count * self.gui_frameSpan + i, self.gui_frameSpan * self.frame_count)
        # Process pending events to update the GUI
        QtWidgets.QApplication.processEvents()

        # Mark the analysis as completed - from now on cached data will be accessed
        self.is_analyzed[self.type - 1] = True
        print("done")
        self.displayGraph()


    def generate_color(self, value):
        if value <= self.gui_colorBorderValue:
            scaled_value = value / self.gui_colorBorderValue
            cmap = mcolors.LinearSegmentedColormap.from_list('custom_cmap', [self.gui_color1, self.gui_color2])  # Orange --> Red
        else:
            scaled_value = (value - self.gui_colorBorderValue) / (1 - self.gui_colorBorderValue)
            cmap = mcolors.LinearSegmentedColormap.from_list('custom_cmap', [self.gui_color2, self.gui_color4])  # Red --> Black

        color = cmap(scaled_value)
        hex_code = mcolors.rgb2hex(color)
        return hex_code



    def displayGraph(self):
        global silent_noGui

        # Convert frame count to time in seconds for x-axis
        time = [i / self.fps for i in range(len(self.brightness[0]))]

        # Create a plot to display the results and make it quite wide and gray in background
        fig, ax = plt.subplots(figsize=(15, 5))

        # Set the background color based on y-values
        ax.axhspan(0, 20, facecolor='#00ff00', alpha=0.4, edgecolor='none')     # lime
        ax.axhspan(20, 25, facecolor='#7dff00', alpha=0.4, edgecolor='none')
        ax.axhspan(25, 30, facecolor='#b1ff00', alpha=0.4, edgecolor='none')
        ax.axhspan(30, 35, facecolor='#dbff00', alpha=0.4, edgecolor='none')
        ax.axhspan(35, 60, facecolor='#ffff00', alpha=0.4, edgecolor='none')    # yellow
        ax.axhspan(60, 65, facecolor='#ffdc00', alpha=0.4, edgecolor='none')
        ax.axhspan(65, 70, facecolor='#ffb900', alpha=0.4, edgecolor='none')
        ax.axhspan(70, 75, facecolor='#ff9600', alpha=0.4, edgecolor='none')
        ax.axhspan(75, 80, facecolor='#ff7200', alpha=0.4, edgecolor='none')    # orange
        ax.axhspan(80, 85, facecolor='#ff6200', alpha=0.4, edgecolor='none')
        ax.axhspan(85, 90, facecolor='#ff4e00', alpha=0.4, edgecolor='none')
        ax.axhspan(90, 95, facecolor='#ff3600', alpha=0.4, edgecolor='none')
        ax.axhspan(95, 100, facecolor='#ff0000', alpha=0.4, edgecolor='none')   # red
        ax.axhspan(100, self.gui_yLim, facecolor='#950101', alpha=0.4, edgecolor='none')

        print("plotting begins shortly. type=" + str(self.type))
        # TODO: Seemingly stuck to self.type==1

        if (self.type == 1):
            # Create a plot to display the results for absolute brightness values
            print("Plotting absolute brightness plots as requested")
            # The number of plots will either be equal to gui_maxSpan, but limited to gui_plotColors
            print(str(self.gui_frameSpan) + " plots calculated, a maximum of " + str(self.gui_plotMaxColors) + " can be drawn")
            if (self.gui_frameSpan<=self.gui_plotMaxColors):
                print("Plotting " + str(self.gui_frameSpan) + " plots as requested")
                for i in range(0, self.gui_frameSpan):
                    hex_code = self.generate_color(i / self.gui_frameSpan)
                    opacity = i / self.gui_plotMaxColors
                    # print(hex_code)
                    plt.plot(time, self.brightness_absolute[i], label='span='+str(i), color=hex_code, alpha=opacity)
            else:
                print(str(self.gui_frameSpan) + " plots calculated but only " + str(self.gui_plotMaxColors) + " will be drawn")
                for i in range(0, self.gui_plotMaxColors):
                    hex_code = self.generate_color(i / self.gui_plotMaxColors)
                    opacity = i / self.gui_plotMaxColors
                    # print(hex_code)
                    plt.plot(time, self.brightness_absolute[math.floor((i / self.gui_plotMaxColors) * (self.gui_frameSpan - 1))], label='span=' + str(math.floor((i / self.gui_plotMaxColors) * (self.gui_frameSpan - 1))), color=hex_code, alpha=opacity)
        elif (self.type == 2):
            # TODO: Implement perceived self.brightness
            print("...")
        elif (self.type == 3):
            # Create a plot to display the results for R, G and B separately
            print("Plotting R, G and B plots as requested")
            # The number of plots will either be equal to gui_maxSpan, but limited to gui_plotColors
            print(str(self.gui_frameSpan) + " plots calculated, a maximum of " + str(self.gui_plotMaxColors) + " can be drawn")
            plt.plot(time, self.brightness_channel_R[0], label='RED', color='#ff0000')
            plt.plot(time, self.brightness_channel_G[0], label='GREEN', color='#00ff00')
            plt.plot(time, self.brightness_channel_B[0], label='BLUE', color='#0000ff')
        else:
            print("ERROR: Unknown analysis mode selected for plotting: " + str(self.type))
            return



        plt.xlabel('Time (s)')
        plt.ylabel('Change in self.brightness')
        plt.ylim(0, self.gui_yLim)
        # plt.legend()

        if (silent_noGui):
            print("Silent mode, not displaying graphs")
            plt.savefig(self.file_path+'.png')
            print("Saved as "+self.file_path+'.png')
        else:
            print("Plotting in 3... 2... 1...")
            plt.show()

    def det_brightness_absolute(self):
        # Iterate over video frames
        for i in range(0, self.frame_count):
            is_validFrame, frame = self.cap.read()
            if not is_validFrame:
                # Checking for unexpected EoF
                print("No next frame found")
                break

            # Determine absolute self.brightness of current video frame
            self.brightness[0][i] = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean()

            # Update GUI to track progress
            if i % 100 == 0:
                self.reportStatus("Step 1/2 (collecting data)", i, self.frame_count)
                # Process pending events to update the GUI
                QtWidgets.QApplication.processEvents()


    def det_brightness_perceived(self):
        # Iterate over video frames
        for i in range(0, self.frame_count):
            is_validFrame, frame = self.cap.read()
            if not is_validFrame:
                # Checking for unexpected EoF
                break

            # Determine perceived self.brightness of current video frame
            self.brightness[1][i] = 0
            # TODO

            # Update GUI to track progress
            if i % 100 == 0:
                self.reportStatus("Step 1/2 (collecting data)", i, self.frame_count)
                # Process pending events to update the GUI
                QtWidgets.QApplication.processEvents()


    def det_brightness_separate(self):
        # Iterate over video frames
        for i in range(0, self.frame_count):
            is_validFrame, frame = self.cap.read()
            if not is_validFrame:
                # Checking for unexpected EoF
                break

            # Determine self.brightness of R, G and B channels of current video frame separately

            # Split the frame into its color channels (B, G, R)
            b, g, r = cv2.split(frame)

            # Calculate the average values for each color channel
            self.brightness[2][i] = numpy.mean(r)    # red
            self.brightness[3][i] = numpy.mean(g)    # green
            self.brightness[4][i] = numpy.mean(b)    # blue

            # Update GUI to track progress
            if i % 100 == 0:
                self.reportStatus("Step 1/2 (collecting data)", i, self.frame_count)
                # Process pending events to update the GUI
                QtWidgets.QApplication.processEvents()


    def reportStatus(self, task, current_frame, progress_count=100):
        percent_done = int(current_frame / self.frame_count * 100)
        self.progressBar.setValue(percent_done)
        status = f"{task} - Processing frame {current_frame} of {progress_count}... {percent_done}% done."
        self.label_progress.setText(status)
        print(status)


# Create an instance of the widget
app = QtWidgets.QApplication([])
window = MainWindow()
window.show()

# Get initial values, so they don't differ from GUI contents
window.gui_apply_settings_changes()
window.gui_apply_graphics_changes()


# Run the application event loop
sys.exit(app.exec())