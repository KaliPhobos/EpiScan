#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 31 13:20:04 2023
@author: KaliPhobos
"""
import math
import numpy
from PyQt6 import QtWidgets, uic
import sys
import cv2
import os
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Initialize all vars
type = 1  # The currently selected method how brightness should be handled
type_1 = "Absolute brightness"  # String for method 1
type_2 = "Perceived brightness"  # String for method 2
type_3 = "R,G,B as separate channels"  # String for method 3
fps = 0
file_path = ''  # Path to the video file
file_path_old = ''  # Path to the previously processed video file
gui_isResetForced = False  # Should all cached data be deleted instead of reused?
brightness = numpy.zeros((5, 2))  # The array containing all resulting raw data
brightness_absolute = numpy.zeros((2, 2))
brightness_perceived = numpy.zeros((2, 2))
brightness_channel_R = numpy.zeros((2, 2))
brightness_channel_G = numpy.zeros((2, 2))
brightness_channel_B = numpy.zeros((2, 2))
is_analyzed = [False, False, False]  # Was an analysis on a already completed? (Array of booleans)
cap = None  # Contains all frames
gui_frameSpan = 20 # Current width of the analysis span
gui_plotMaxColors = 20 # Number of plots to be drawn if the analysis span exceeds 10
gui_colorBorderValue = 0.3  # Value (0...1) at which the second color should be placed in the linear gradient
gui_color1 = '#FF7000'  # Color 1 for 3-color linear gradient coloring of data plots
gui_color2 = '#FF0000'  # Color 2 for 3-color linear gradient coloring of data plots
gui_color3 = '#000000'  # Color 3 for 3-color linear gradient coloring of data plots
gui_yLim = 120  # Maximum Y-Value for plots

"""
Table 'brightness' contains the raw brightness values split into 5 lines:
1. line (0): The absolute brightness for each frame
2. line (1): The perceived brightness for each frame (thx D. Finley, alienryderflex.com/hsp.html)
3. line (2): The R-channels brightness for each frame
4. line (3): The G-channels brightness for each frame
5. line (4): The B-channels brightness for each frame
Table 'brightness_absolute' contains statistics across X lines, X being the max span according to settings
1. line (0): The absolute brightness changes across 2 neighboring frames (starting with the first)
2. line (1): The absolute brightness changes across 3 neighboring frames (starting with the first)
3. line (2): The absolute brightness changes across 4 neighboring frames (starting with the first) and so on
Table 'brightness_perceived' does the same but uses the perceived instead of actual brightness as base data
Table 'brightness_channel_R' does the same but uses the R-channel only as base data
Table 'brightness_channel_G' does the same but uses the R-channel only as base data
Table 'brightness_channel_B' does the same but uses the R-channel only as base data
"""
class MainWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        global file_path
        uic.loadUi("EpiScan_GUI.ui", self)
        self.button_load.clicked.connect(self.gui_load_file)
        self.button_applyGraphics.clicked.connect(self.gui_apply_graphics_changes)
        self.button_applySettings.clicked.connect(self.gui_apply_settings_changes)
        self.button_processFile.clicked.connect(lambda: self.gui_forced_processFile(file_path))
        self.button_processData.clicked.connect(self.gui_forced_processData) # Re-process all collected data on video file (forced)
        self.button_drawGraph.clicked.connect(self.gui_forced_displayGraph) # Re-draw graph using given results (forced)

    def gui_forced_processFile(self, file_path):
        global file_path_old
        if os.path.isdir(file_path):
            print("Please select a file, not a folder")
            return
        if os.path.isfile(file_path):
            print("Provided file: " + str(file_path))
        else:
            print("Please select a file")
            return
        if (file_path == file_path_old):
            print("Duplicate file... Click again to ignore & analyze")
            file_path_old = ""
            return
        file_path_old = file_path
        self.button_load.setText("Abort")
        processFile(file_path, self)

    def gui_forced_processData(self):
        processData(self)

    def gui_forced_displayGraph(self):
        displayGraph(self)

    def gui_load_file(self):
        # Read the new file path and forward it
        self.gui_forced_processFile(self.lineEdit_filePath.text())



    # Apply changes in GUI controls so they can be considered
    def gui_apply_settings_changes(self):
        global gui_frameSpan, gui_plotMaxColors, gui_isResetForced
        print("APPLY SETTINGS CHANGES!")
        # Apply changes in GUI
        gui_frameSpan = self.spinBox_frameSpan.value()
        print("Set: gui_frameSpan = " + str(gui_frameSpan))
        gui_isResetForced = self.checkBox_isResetForced.isChecked()
        print("Set: gui_isResetForced = " + str(gui_isResetForced))
        gui_plotMaxColors = self.spinBox_plotMaxColors.value()
        print("Set: gui_plotMaxColors = " + str(gui_plotMaxColors))
        processData(self)

    def gui_apply_graphics_changes(self):
        global gui_colorBorderValue, gui_color1, gui_color2, gui_color3, gui_yLim
        print("APPLY GRAPHICS CHANGES!")
        # Apply changes in GUI

        gui_colorBorderValue = self.doubleSpinBox_colorBorderValue.value()
        print("Set: gui_colorBorderValue = " + str(gui_colorBorderValue))
        gui_color1 = self.lineEdit_color1.text()
        print("Set: gui_color1 = " + str(gui_color1))
        gui_color2 = self.lineEdit_color2.text()
        print("Set: gui_color2 = " + str(gui_color2))
        gui_color3 = self.lineEdit_color3.text()
        print("Set: gui_color3 = " + str(gui_color3))
        gui_yLim = self.spinBox_yLim.value()
        print("Set: gui_yLim = " + str(gui_yLim))




def processFile(file_path, ui): # Read the contents of a given video file and analyze each frame
    global brightness_absolute, brightness_perceived, brightness_channel_R, brightness_channel_G, brightness_channel_B
    global gui_frameSpan
    global gui_isResetForced, brightness
    global type_1, type_2, type_3
    global type
    global fps
    global cap

    # Load the video and determine number of frames and fps
    print("Load File " + str(file_path))
    cap = cv2.VideoCapture(file_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Check if the file has been analyzed before and a .csv file with the results is available
    if (os.path.isfile(file_path+".csv")):
        # Load the data from the CSV file
        brightness = numpy.loadtxt(file_path + ".csv", delimiter=',')
        print("File " + file_path + ".csv found, restoring data...")
    else:
        # Check if cached data is supposed to be deleted & create new arrays if necessary
        checkCacheState()
        # Same for raw data
        if (file_path_old != file_path or gui_isResetForced or len(brightness[0]) != frame_count or cap == None):
            brightness = numpy.zeros((5, frame_count))

        # Determine the selected brightness option
        brightness_type = ui.comboBox_brightness.currentText()
        match brightness_type:
            case str(type_1):
                type = 1
                print("Analysis on " + str(type_1))
                det_brightness_absolute(cap, frame_count, ui)
            case str(type_2):
                type = 2
                print("Analysis on " + str(type_2))
                det_brightness_perceived(cap, frame_count, ui)
            case str(type_2):
                type = 3
                print("Analysis on " + str(type_3))
                det_brightness_separate(cap, frame_count, ui)
            case _:
                print("ERROR: Unknown analysis mode selected")
                return

        # Step 1 completed, data from all frames has been collected
        reportStatus(ui, "Step 1/2 completed, pushing data to file...", frame_count, frame_count)

        # Save the brightness array to a CSV file
        numpy.savetxt(file_path+'.csv', brightness, delimiter=',')

    ui.button_load.setText("LOAD")
    # Process pending events to update the GUI
    QtWidgets.QApplication.processEvents()
    processData(ui)


def processData(ui):
    # Prepare variables
    global brightness_absolute, brightness_perceived, brightness_channel_R, brightness_channel_G, brightness_channel_B
    global type, brightness, is_analyzed, gui_frameSpan, cap
    frame_count = len(brightness[0])

    # Check if cached data is supposed to be deleted & create new arrays if necessary
    checkCacheState()

    if (type == 1 and len(brightness_absolute) < gui_frameSpan):
        print("additional lines required as gui_maxSpan was increased")

    for i in range(0, len(is_analyzed)):
        print("DEBUG: is_analyzed[" + str(i) + "] is " + str(is_analyzed[i]))

    # Check if processing is even necessary
    if (cap == None):
        print("No video file has been selected. Returning.")
        return

    if (is_analyzed[type - 1] == True):
        # Report current status
        print("Cached data found, no new analysis necessary.")
        reportStatus(ui, "Step 2/2 (processing CACHED data)", len(brightness[0]), len(brightness[0]))
        QtWidgets.QApplication.processEvents()
        # Display graph from cached data, then return
        displayGraph(ui)
        return

    # Report current status
    reportStatus(ui, "Step 2/2 (analyzing data) begins...", 0)
    QtWidgets.QApplication.processEvents()

    # Create separate statistics for each frame span
    print("DEBUG: frame_span is 2..." + str(gui_frameSpan))
    for frame_span in range(1, gui_frameSpan):
        # Iterate over all video frames (except the last X frames, X being the current frame span)
        print("DEBUG: i is 0..." + str(frame_count - frame_span - 1))
        for i in range(0, frame_count - frame_span):
            # Absolute brightness analysis
            if (type == 1):
                value = 0
                # print("DEBUG: j is " + str(i) + "..." + str(i + frame_span))
                for j in range(i, i + frame_span):
                    # Sum up changes across the current frame span
                    value += abs(brightness[type - 1, j] - brightness[type - 1, j + 1])
                brightness_absolute[frame_span - 1][i] = value / (0.7 * frame_span)

            # Perceived brightness analysis
            if (type == 2):
                value = 0
                for j in range(i, i + frame_span):
                    # Sum up changes across the current frame span
                    value += abs(brightness[type - 1, j] - brightness[type - 1, j + 1])
                brightness_perceived[frame_span - 1][i] = value

            # Separate analysis for each channel
            if (type == 3):
                value = [0, 0, 0]
                for j in range(i, i + frame_span):
                    # Sum up changes across the current frame span
                    value[0] += abs(brightness[type - 1, j] - brightness[type - 1, j + 1])
                    value[1] += abs(brightness[type, j] - brightness[type, j + 1])
                    value[2] += abs(brightness[type + 1, j] - brightness[type + 1, j + 1])
                brightness_channel_R[frame_span - 1][i] = value[0]
                brightness_channel_R[frame_span - 1][i] = value[1]
                brightness_channel_R[frame_span - 1][i] = value[2]

            if (type != 1 and type != 2 and type != 3):
                print("ERROR: Unknown analysis mode selected")
                return

            # Update GUI to track progress
            if (i % 10000 == 0):
                reportStatus(ui, "Step 2/2 (analyzing data)", frame_count * frame_span + i, gui_frameSpan * (frame_count - gui_frameSpan / 2))
                # Process pending events to update the GUI
                QtWidgets.QApplication.processEvents()

    reportStatus(ui, "Step 2/2 (analyzing data)", frame_count * frame_span + i, gui_frameSpan * frame_count)
    # Process pending events to update the GUI
    QtWidgets.QApplication.processEvents()

    # Mark the analysis as completed - from now on cached data will be accessed
    is_analyzed[type - 1] = True
    print("done")
    displayGraph(ui)


def checkCacheState(): # Check if cached data is supposed to be deleted & create new arrays if necessary
    global brightness_absolute, brightness_perceived, brightness_channel_R, brightness_channel_G, brightness_channel_B
    global gui_frameSpan
    global gui_isResetForced, brightness
    global type_1, type_2, type_3
    global type
    global fps
    global cap
    # TODO: How to handle cases in which only gui_maxSpan is getting increased? Cached data should then be used but new data added
    frame_count = len(brightness[0])
    if (file_path_old != file_path or gui_isResetForced or len(brightness[0]) != frame_count or cap == None):
        print("deleted cached data")
        brightness_absolute = numpy.zeros((gui_frameSpan, frame_count))
        brightness_perceived = numpy.zeros((gui_frameSpan, frame_count))
        brightness_channel_R = numpy.zeros((gui_frameSpan, frame_count))
        brightness_channel_G = numpy.zeros((gui_frameSpan, frame_count))
        brightness_channel_B = numpy.zeros((gui_frameSpan, frame_count))
        is_analyzed = [False, False, False]
    else:
        print("cached data will not be deleted")


def generate_color(value):
    global gui_color1, gui_color2, gui_color3
    global gui_colorBorderValue
    if value <= gui_colorBorderValue:
        scaled_value = value / gui_colorBorderValue
        cmap = mcolors.LinearSegmentedColormap.from_list('custom_cmap', [gui_color1, gui_color2])  # Orange --> Red
    else:
        scaled_value = (value - gui_colorBorderValue) / (1 - gui_colorBorderValue)
        cmap = mcolors.LinearSegmentedColormap.from_list('custom_cmap', [gui_color2, gui_color3])  # Red --> Black

    color = cmap(scaled_value)
    hex_code = mcolors.rgb2hex(color)
    return hex_code



def displayGraph(ui):
    global type, fps, gui_frameSpan, gui_plotMaxColors, brightness, gui_yLim

    # Convert frame count to time in seconds for x-axis
    time = [i / fps for i in range(len(brightness[0]))]

    # Create a plot to display the results and make it quite wide and gray in background
    fig, ax = plt.subplots(figsize=(15, 5))

    # Set the colors to turn from yellowish towards red rather quickly
    color_border_value = 0.3

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
    ax.axhspan(100, gui_yLim, facecolor='#950101', alpha=0.4, edgecolor='none')

    # Create a plot to display the results
    # The number of plots will either be equal to gui_maxSpan, but limited to gui_plotColors
    print(str(gui_frameSpan) + " plots calculated, a maximum of " + str(gui_plotMaxColors) + " can be drawn")
    if (gui_frameSpan<=gui_plotMaxColors):
        print("Plotting " + str(gui_frameSpan) + " plots as requested")
        for i in range(0, gui_frameSpan):
            hex_code = generate_color(i / gui_frameSpan)
            opacity = i / gui_plotMaxColors
            print(hex_code)
            plt.plot(time, brightness_absolute[i], label='span='+str(i), color=hex_code, alpha=opacity)
    else:
        print(str(gui_frameSpan) + " plots calculated but only " + str(gui_plotMaxColors) + " will be drawn")
        for i in range(0, gui_plotMaxColors):
            hex_code = generate_color(i / gui_plotMaxColors)
            opacity = i / gui_plotMaxColors
            print(hex_code)
            plt.plot(time, brightness_absolute[math.floor((i / gui_plotMaxColors) * (gui_frameSpan - 1))], label='span=' + str(math.floor((i / gui_plotMaxColors) * (gui_frameSpan - 1))), color=hex_code, alpha=opacity)
    plt.xlabel('Time (s)')
    plt.ylabel('Change in Brightness')
    plt.ylim(0, gui_yLim)
    # plt.legend()
    plt.show()

def det_brightness_absolute(cap, frame_count, ui):
    global brightness
    # Iterate over video frames
    for i in range(0, frame_count):
        is_validFrame, frame = cap.read()
        if not is_validFrame:
            # Checking for unexpected EoF
            break

        # Determine absolute brightness of current video frame
        brightness[0][i] = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean()

        # Update GUI to track progress
        if i % 100 == 0:
            reportStatus(ui, "Step 1/2 (collecting data)", i, frame_count)
            # Process pending events to update the GUI
            QtWidgets.QApplication.processEvents()


def det_brightness_perceived(cap, frame_count, ui):
    global brightness
    # Iterate over video frames
    for i in range(0, frame_count):
        is_validFrame, frame = cap.read()
        if not is_validFrame:
            # Checking for unexpected EoF
            break

        # Determine perceived brightness of current video frame
        brightness[1][i] = 0
        # TODO

        # Update GUI to track progress
        if i % 100 == 0:
            reportStatus(ui, "Step 1/2 (collecting data)", i, frame_count)
            # Process pending events to update the GUI
            QtWidgets.QApplication.processEvents()


def det_brightness_separate(cap, frame_count, ui):
    global brightness
    # Iterate over video frames
    for i in range(0, frame_count):
        is_validFrame, frame = cap.read()
        if not is_validFrame:
            # Checking for unexpected EoF
            break

        # Determine brightness of R, G and B channels of current video frame separately
        brightness[2][i] = 0
        brightness[3][i] = 0
        brightness[4][i] = 0
        # TODO

        # Update GUI to track progress
        if i % 100 == 0:
            reportStatus(ui, "Step 1/2 (collecting data)", i, frame_count)
            # Process pending events to update the GUI
            QtWidgets.QApplication.processEvents()


def reportStatus(ui, task, current_frame, frame_count=100):
    percent_done = int(current_frame / frame_count * 100)
    ui.progressBar.setValue(percent_done)
    status = f"{task} - Processing frame {current_frame} of {frame_count}... {percent_done}% done."
    ui.label_progress.setText(status)
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