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
types = [] # Holds the names for all methods to analyse the data, used to match the type
types.append("Absolute brightness")  # String for method 1
types.append("Perceived brightness")  # String for method 2
types.append("R,G,B as separate channels")  # String for method 3


"""
Table 'brightness' contains the raw brightness values split into 5 lines:
1. line (0): The absolute brightness for each frame
2. line (1): The perceived brightness for each frame (thx D. Finley, alienryderflex.com/hsp.html)
3. line (2): The R-channels brightness for each frame
4. line (3): The G-channels brightness for each frame
5. line (4): The B-channels brightness for each frame
Table 'brightnessAbsolute' contains statistics across X lines, X being the max span according to settings
1. line (0): The absolute brightness changes across 2 neighboring frames (starting with the first)
2. line (1): The absolute brightness changes across 3 neighboring frames (starting with the first)
3. line (2): The absolute brightness changes across 4 neighboring frames (starting with the first) and so on
Table 'brightnessPerceived' does the same but uses the perceived instead of actual brightness as base data
Table 'brightnessChannelR' does the same but uses the R-channel only as base data
Table 'brightnessChannelG' does the same but uses the R-channel only as base data
Table 'brightnessChannelB' does the same but uses the R-channel only as base data
"""



class Job:
    def __init__(self):
        self.file_path = "" # Path to the current job's video file
        self.file_path_old = "" # Path to the previously processed video file
        self.job_type = ""
        self.is_silent_mode = False

    def set_type(self, type):
        self.type = type    # Type of the current job, int 1...3 are valid
        # TODO: Maybe an enum would be simpler?

    def set_fps(self, fps):
        self.fps = fps  # frames per second for the current job

    def set_isResetForced(self, is_forced):
        self.is_resetForced = is_forced # Should all cached data be deleted instead of reused?

    def set_cap(self, cap):
        self.cap = cap  # Contains all frames

    def set_frameSpan(self, frameSpan):
        self.frameSpan = frameSpan  # Current frame width of the analysis span
    
    def set_plotMaxColors(self, plotMaxColors):
        self.plotMaxColors = plotMaxColors  # Number of plots to be drawn if the analysis span exceeds 10

    def set_colorBorderValue(self, colorBorderValue):
        self.colorBorderValue = colorBorderValue  # Value (0...1) at which the second color should be placed in the linear gradient
        
    def set_color1(self, color):
        self.color1 = color  # Color 1 for 3-color linear gradient coloring of data plots

    def set_color2(self, color):
        self.color2 = color  # Color 2 for 3-color linear gradient coloring of data plots

    def set_color3(self, color):
        self.color3 = color  # Color 3 for 3-color linear gradient coloring of data plots

    def set_yLim(self, y_limit):
        self.yLim = y_limit  # Maximum Y-Value for plots

    def set_timestampStart(self):
        print("...")    # Track the timestamp at which processing begins

    def set_analyzed(self, type, is_analyzed):
        self.is_analyzed[type] = is_analyzed    # Was an analysis already completed? (Array of booleans)

class MainWindow(QtWidgets.QDialog):
    def __init__(self, current_job):
        super().__init__()
        # Initialize all vars
        self.job = current_job
        self.job.set_type(0)  # The currently selected method how brightness should be handled (1...3 are valid)
        self.job.set_fps(0)
        self.job.set_isResetForced(True)  # Should all cached data be deleted instead of reused?
        self.job.brightness = numpy.zeros((5, 2))  # The array containing all resulting raw data
        self.job.brightnessAbsolute = numpy.zeros((2, 2))
        self.job.brightnessPerceived = numpy.zeros((2, 2))
        self.job.brightnessChannelR = numpy.zeros((2, 2))
        self.job.brightnessChannelG = numpy.zeros((2, 2))
        self.job.brightnessChannelB = numpy.zeros((2, 2))
        self.job.is_analyzed = [False, False, False]  # Was an analysis already completed? (Array of booleans)
        self.job.set_cap(None)  # Contains all frames
        self.job.set_frameSpan(20)  # Current frame width of the analysis span
        self.job.set_plotMaxColors(20)  # Number of plots to be drawn if the analysis span exceeds 10
        self.job.set_colorBorderValue(0.8)  # Value (0...1) at which the second color should be placed in the linear gradient
        self.job.set_color1('#FF7000')  # Color 1 for 3-color linear gradient coloring of data plots
        self.job.set_color2('#FF0000')  # Color 2 for 3-color linear gradient coloring of data plots
        self.job.set_color3('#000000')  # Color 3 for 3-color linear gradient coloring of data plots
        self.job.set_yLim(120)  # Maximum Y-Value for plots

        uic.loadUi("EpiScan_GUI.ui", self)
        self.button_load.clicked.connect(lambda: self.gui_loadFile(self.lineEdit_filePath.text()))  # Apply path & load file
        self.button_applyGraphics.clicked.connect(self.gui_apply_graphics_changes)
        self.button_applySettings.clicked.connect(self.gui_apply_settings_changes)
        self.button_processFile.clicked.connect(self.gui_loadFile)
        self.button_processData.clicked.connect(self.gui_forced_processData) # Re-process all collected data on video file (forced)
        self.button_drawGraph.clicked.connect(self.gui_forced_displayGraph) # Re-draw graph using given results (forced)

    def gui_loadFile(self, file_path):
        if os.path.isdir(file_path):
            print("Please select a file, not a folder: " + file_path)
            return
        if os.path.isfile(file_path):
            print("Provided file: " + file_path)
        else:
            print("Please select a file. given: " + file_path)
            return
        if (file_path == self.job.file_path_old):
            print("Duplicate file... Click again to ignore & analyze")
            # TODO: Also show feedback in GUI
            self.job.file_path_old = ""
            return
        self.job.file_path_old = self.job.file_path
        self.job.file_path = file_path  # Filepath is valid. Apply so it can be processed
        self.processFile()

    def gui_forced_processData(self):
        self.processData()

    def gui_forced_displayGraph(self):
        self.displayGraph()

    # Apply changes in GUI controls so they can be considered
    def gui_apply_settings_changes(self):
        print("APPLY SETTINGS CHANGES!")
        # Apply changes in GUI
        self.job.set_frameSpan(self.spinBox_frameSpan.value())
        print("Set: frameSpan = " + str(self.job.frameSpan))
        self.job.set_isResetForced(self.checkBox_isResetForced.isChecked())
        print("Set: is_resetForced = " + str(self.job.is_resetForced))
        self.job.set_plotMaxColors(self.spinBox_plotMaxColors.value())
        print("Set: plotMaxColors = " + str(self.job.plotMaxColors))


    def gui_apply_graphics_changes(self):
        print("APPLY GRAPHICS CHANGES!")
        # Apply changes in GUI

        # TODO: use job object's setters
        self.job.colorBorderValue = self.doubleSpinBox_colorBorderValue.value()
        print("Set: gui_colorBorderValue = " + str(self.job.colorBorderValue))
        self.job.color1 = self.lineEdit_color1.text()
        print("Set: gui_color1 = " + str(self.job.color1))
        self.job.color2 = self.lineEdit_color2.text()
        print("Set: gui_color2 = " + str(self.job.color2))
        self.job.color3 = self.lineEdit_color3.text()
        print("Set: gui_color4 = " + str(self.job.color3))
        self.job.yLim = self.spinBox_yLim.value()
        print("Set: gui_yLim = " + str(self.job.yLim))

    def processFile(self): # Read the contents of a given video file and analyze each frame
        global types
        # Load the video and determine number of frames and self.fps
        print("Load File " + str(self.job.file_path))
        self.button_load.setText("Abort")
        self.cap = cv2.VideoCapture(self.job.file_path)
        self.job.frameCount = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))

        # Check if the file has been analyzed before and a .csv file with the results is available
        if (os.path.isfile(self.job.file_path+".csv")):
            # Load the data from the CSV file
            self.job.brightness = numpy.loadtxt(self.job.file_path + ".csv", delimiter=',')
            print("File " + self.job.file_path + ".csv found, restoring data...")
            # Check if analysis type 1 results are contained in .csv data
            self.job.set_analyzed(0, (not all(value == '0' for value in self.job.brightness[0])))
            # Check if analysis type 2 results are contained in .csv data
            self.job.set_analyzed(1, (not all(value == '0' for value in self.job.brightness[1])))
            # Check if analysis type 3 results are contained in .csv data
            self.job.set_analyzed(2, (not all(value == '0' for value in self.job.brightness[2])))
            if (not all(value == '0' for value in self.job.brightness[2])):
                self.job.set_analyzed(2, True)
            elif (not all(value == '0' for value in self.job.brightness[2])):
                self.job.set_analyzed(2, True)
        else:
            print("No file '" + self.job.file_path + ".csv' with cached data found. Will have to analyze file")

            # Check if a new file has been selected, so old data has to be purged
            if (self.job.file_path_old != self.job.file_path or self.gui_isResetForced or self.cap == None or len(self.job.brightness[0]) != int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))):
                self.job.brightness = numpy.zeros((5, self.job.frameCount))
                self.job.brightnessAbsolute = numpy.zeros((self.job.frameSpan, self.job.frameCount))
                self.job.brightnessPerceived = numpy.zeros((self.job.frameSpan, self.job.frameCount))
                self.job.brightnessChannelR = numpy.zeros((self.job.frameSpan, self.job.frameCount))
                self.job.brightnessChannelG = numpy.zeros((self.job.frameSpan, self.job.frameCount))
                self.job.brightnessChannelB = numpy.zeros((self.job.frameSpan, self.job.frameCount))
                self.job.is_analyzed = [False, False, False]


        # Determine the selected self.job.brightness option
        self.job.brightness_type = self.comboBox_brightness.currentText()
        print("Trying to match analysis mode '" + str(self.job.brightness_type) + '\'')
        print("Available options: ")
        print("1: '" + str(types[0]) + '\'')
        print("2: '" + str(types[1]) + '\'')
        print("3: '" + str(types[2]) + '\'')

        if (self.job.brightness_type == types[0]):
            self.job.type = 1
            print("Analysis on " + str(types[0]))
            self.calc_brightnessAbsolute()
        elif (self.job.brightness_type == types[1]):
            self.job.type = 2
            print("Analysis on " + str(types[1]))
            self.calc_brightnessPerceived()
        elif (self.job.brightness_type == types[2]):
            self.job.type = 3
            print("Analysis on " + str(types[2]))
            self.calc_brightnessSeparate()
        else:
            print("ERROR: Unknown analysis mode selected: " + str(self.job.type))
            return

        # Step 1 completed, data from all frames has been collected
        self.reportStatus("Step 1/2 completed, pushing data to file...", self.job.frameCount, self.job.frameCount)

        # Save the self.job.brightness array to a CSV file
        print("Saving data to: " + self.job.file_path+'.csv')
        numpy.savetxt(self.job.file_path+'.csv', self.job.brightness, delimiter=',')

        self.button_load.setText("LOAD")
        # Process pending events to update the GUI
        QtWidgets.QApplication.processEvents()
        self.processData()


    def processData(self):

        # Check if cached data is supposed to be deleted & create new arrays if necessary
        # TODO: How to handle cases in which only gui_maxSpan is getting increased? Cached data should then be used but new data added
        if (self.job.file_path_old != self.job.file_path or self.gui_isResetForced or self.cap == None or len(self.job.brightness[0]) != int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))):
            print("set brightness data arrays to appropriate size")
            self.job.brightnessAbsolute = numpy.zeros((self.job.frameSpan, self.job.frameCount))
            self.job.brightnessPerceived = numpy.zeros((self.job.frameSpan, self.job.frameCount))
            self.job.brightnessChannelR = numpy.zeros((self.job.frameSpan, self.job.frameCount))
            self.job.brightnessChannelG = numpy.zeros((self.job.frameSpan, self.job.frameCount))
            self.job.brightnessChannelB = numpy.zeros((self.job.frameSpan, self.job.frameCount))
            self.job.is_analyzed = [False, False, False]
        else:
            print("cached data looks good, will not be deleted")

        if (self.job.type == 1 and len(self.job.brightnessAbsolute) < self.job.frameSpan):
            print("additional lines required as gui_maxSpan was increased")

        for i in range(0, len(self.job.is_analyzed)):
            print("DEBUG: is_analyzed[" + str(i) + "] is " + str(self.job.is_analyzed[i]))

        # Check if processing is even necessary
        if (self.cap == None):
            print("No video file has been selected. Returning.")
            return

        print("self.job.brightnessAbsolute is of size " + str(len(self.job.brightnessAbsolute)) + "x" + str(len(self.job.brightnessAbsolute[0])))

        if (self.job.is_analyzed[self.job.type - 1] == True):
            # Report current status
            print("Cached data found, no new analysis necessary.")
            self.reportStatus("Step 2/2 (processing CACHED data)", len(self.job.brightness[0]), len(self.job.brightness[0]))
            QtWidgets.QApplication.processEvents()
            # Display graph from cached data, then return
            self.displayGraph()
            return

        # Report current status
        self.reportStatus("Step 2/2 (analyzing data) begins...", 0)
        QtWidgets.QApplication.processEvents()

        # Create separate statistics for each frame span
        print("DEBUG: Frame spans in which brightness changes will be calculated) are 2..." + str(self.job.frameSpan) + " (max value, 'frame_span')")
        for frame_span in range(1, self.job.frameSpan):
            # Iterate over all video frames (except the last X frames, X being the current frame span)
            print("DEBUG: span=" + str(frame_span) + ", iterating over frames 0..." + str(self.job.frameCount - frame_span - 1) + " (will decrease as span size is going up)")
            for i in range(0, self.job.frameCount - frame_span):
                # Absolute self.job.brightness analysis
                if (self.job.type == 1):
                    value = 0
                    # print("DEBUG: j is " + str(i) + "..." + str(i + frame_span))
                    for j in range(i, i + frame_span):
                        # Sum up changes across the current frame span
                        value += abs(self.job.brightness[self.job.type - 1, j] - self.job.brightness[self.job.type - 1, j + 1])
                    self.job.brightnessAbsolute[frame_span - 1][i] = value / (0.7 * frame_span)

                # Perceived self.job.brightness analysis
                elif (self.job.type == 2):
                    value = 0
                    for j in range(i, i + frame_span):
                        # Sum up changes across the current frame span
                        value += abs(self.job.brightness[self.job.type - 1, j] - self.job.brightness[self.job.type - 1, j + 1])
                    self.job.brightnessPerceived[frame_span - 1][i] = value

                # Separate analysis for each channel
                elif (self.job.type == 3):
                    value = [0, 0, 0]
                    for j in range(i, i + frame_span):
                        # Sum up changes across the current frame span
                        value[0] += abs(self.job.brightness[self.job.type - 1, j] - self.job.brightness[self.job.type - 1, j + 1])
                        value[1] += abs(self.job.brightness[self.job.type, j] - self.job.brightness[self.job.type, j + 1])
                        value[2] += abs(self.job.brightness[self.job.type + 1, j] - self.job.brightness[self.job.type + 1, j + 1])
                    self.job.brightnessChannelR[frame_span - 1][i] = value[0]
                    self.job.brightnessChannelR[frame_span - 1][i] = value[1]
                    self.job.brightnessChannelR[frame_span - 1][i] = value[2]

                else:
                    print("ERROR: Unknown analysis mode selected: " + str(self.job.type))
                    return

                # Update GUI to track progress
                if (i % 10000 == 0):
                    self.reportStatus("Step 2/2 (analyzing data)", self.job.frameCount * frame_span + i, self.job.frameSpan * (self.job.frameCount - self.job.frameSpan / 2))
                    # TODO: Numbers appear to be wrong, reached values >>100%
                    # Process pending events to update the GUI
                    QtWidgets.QApplication.processEvents()

                    if (i == 100000):
                        global timestamp_start
                        print("100'000 units processed, calculating ETA")
                        # timestamp_current = datetime.datetime
                        # timestamp_delta = datetime.timedelta(timestamp_current-timestamp_delta)
                        # print(str(timestamp_delta))

        self.reportStatus("Step 2/2 (analyzing data)", self.job.frameCount * self.job.frameSpan + i, self.job.frameSpan * self.job.frameCount)
        # Process pending events to update the GUI
        QtWidgets.QApplication.processEvents()

        # Mark the analysis as completed - from now on cached data will be accessed
        self.job.set_analyzed(self.job.type - 1, True)
        print("done")
        self.displayGraph()


    def generate_color(self, value):
        if value <= self.job.colorBorderValue:
            scaled_value = value / self.job.colorBorderValue
            cmap = mcolors.LinearSegmentedColormap.from_list('custom_cmap', [self.job.color1, self.job.color2])  # Orange --> Red
        else:
            scaled_value = (value - self.job.colorBorderValue) / (1 - self.job.colorBorderValue)
            cmap = mcolors.LinearSegmentedColormap.from_list('custom_cmap', [self.job.color2, self.job.color3])  # Red --> Black

        color = cmap(scaled_value)
        hex_code = mcolors.rgb2hex(color)
        return hex_code



    def displayGraph(self):
        global silent_noGui

        # Convert frame count to time in seconds for x-axis
        time = [i / self.fps for i in range(len(self.job.brightness[0]))]

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
        ax.axhspan(100, self.job.yLim, facecolor='#950101', alpha=0.4, edgecolor='none')

        print("plotting begins shortly. type=" + str(self.job.type))
        # TODO: Seemingly stuck to self.job.type==1

        if (self.job.type == 1):
            # Create a plot to display the results for absolute brightness values
            print("Plotting absolute brightness plots as requested")
            # The number of plots will either be equal to gui_maxSpan, but limited to gui_plotColors
            print(str(self.job.frameSpan) + " plots calculated, a maximum of " + str(self.job.plotMaxColors) + " can be drawn")
            if (self.job.frameSpan<=self.job.plotMaxColors):
                print("Plotting " + str(self.job.frameSpan) + " plots as requested")
                for i in range(0, self.job.frameSpan):
                    hex_code = self.generate_color(i / self.job.frameSpan)
                    opacity = i / self.job.plotMaxColors
                    # print(hex_code)
                    plt.plot(time, self.job.brightnessAbsolute[i], label='span='+str(i), color=hex_code, alpha=opacity)
            else:
                print(str(self.job.frameSpan) + " plots calculated but only " + str(self.job.plotMaxColors) + " will be drawn")
                for i in range(0, self.job.plotMaxColors):
                    hex_code = self.generate_color(i / self.job.plotMaxColors)
                    opacity = i / self.job.plotMaxColors
                    # print(hex_code)
                    plt.plot(time, self.job.brightnessAbsolute[math.floor((i / self.job.plotMaxColors) * (self.job.frameSpan - 1))], label='span=' + str(math.floor((i / self.job.plotMaxColors) * (self.job.frameSpan - 1))), color=hex_code, alpha=opacity)
        elif (self.job.type == 2):
            # TODO: Implement perceived self.job.brightness
            print("...")
        elif (self.job.type == 3):
            # Create a plot to display the results for R, G and B separately
            print("Plotting R, G and B plots as requested")
            # The number of plots will either be equal to gui_maxSpan, but limited to gui_plotColors
            print(str(self.job.frameSpan) + " plots calculated, a maximum of " + str(self.job.plotMaxColors) + " can be drawn")
            plt.plot(time, self.job.brightnessChannelR[0], label='RED', color='#ff0000')
            plt.plot(time, self.job.brightnessChannelG[0], label='GREEN', color='#00ff00')
            plt.plot(time, self.job.brightnessChannelB[0], label='BLUE', color='#0000ff')
        else:
            print("ERROR: Unknown analysis mode selected for plotting: " + str(self.job.type))
            return



        plt.xlabel('Time (s)')
        plt.ylabel('Change in self.job.brightness')
        plt.ylim(0, self.job.yLim)
        # plt.legend()

        if (silent_noGui):
            print("Silent mode, not displaying graphs")
            plt.savefig(self.job.file_path+'.png')
            print("Saved as "+self.job.file_path+'.png')
        else:
            print("Plotting in 3... 2... 1...")
            plt.show()

    def calc_brightnessAbsolute(self):
        # Iterate over video frames
        for i in range(0, self.job.frameCount):
            is_validFrame, frame = self.cap.read()
            if not is_validFrame:
                # Checking for unexpected EoF
                print("No next frame found")
                break

            # Determine absolute self.job.brightness of current video frame
            self.job.brightness[0][i] = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean()

            # Update GUI to track progress
            if i % 100 == 0:
                self.reportStatus("Step 1/2 (collecting data)", i, self.job.frameCount)
                # Process pending events to update the GUI
                QtWidgets.QApplication.processEvents()


    def calc_brightnessPerceived(self):
        # Iterate over video frames
        for i in range(0, self.job.frameCount):
            is_validFrame, frame = self.cap.read()
            if not is_validFrame:
                # Checking for unexpected EoF
                break

            # Determine perceived self.job.brightness of current video frame
            self.job.brightness[1][i] = 0
            # TODO

            # Update GUI to track progress
            if i % 100 == 0:
                self.reportStatus("Step 1/2 (collecting data)", i, self.job.frameCount)
                # Process pending events to update the GUI
                QtWidgets.QApplication.processEvents()


    def calc_brightnessSeparate(self):
        # Iterate over video frames
        for i in range(0, self.job.frameCount):
            is_validFrame, frame = self.cap.read()
            if not is_validFrame:
                # Checking for unexpected EoF
                break

            # Determine self.job.brightness of R, G and B channels of current video frame separately

            # Split the frame into its color channels (B, G, R)
            b, g, r = cv2.split(frame)

            # Calculate the average values for each color channel
            self.job.brightness[2][i] = numpy.mean(r)    # red
            self.job.brightness[3][i] = numpy.mean(g)    # green
            self.job.brightness[4][i] = numpy.mean(b)    # blue

            # Update GUI to track progress
            if i % 100 == 0:
                self.reportStatus("Step 1/2 (collecting data)", i, self.job.frameCount)
                # Process pending events to update the GUI
                QtWidgets.QApplication.processEvents()


    def reportStatus(self, task, current_frame, progress_count=100):
        percent_done = int(current_frame / self.job.frameCount * 100)
        self.progressBar.setValue(percent_done)
        status = f"{task} - Processing frame {current_frame} of {progress_count}... {percent_done}% done."
        self.label_progress.setText(status)
        print(status)





# Create the jobs array and add a first object to it
jobs = [Job()]

# Create an instance of the widget and assign the first job
app = QtWidgets.QApplication([])
window = MainWindow(jobs[0])
window.show()

# Get initial values, so they don't differ from GUI contents
window.gui_apply_settings_changes()
window.gui_apply_graphics_changes()


# Run the application event loop
sys.exit(app.exec())