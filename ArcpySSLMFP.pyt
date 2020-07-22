# -*- coding: utf-8 -*-
# Program Name: ArcpySSLMFP
#   Qingyu Feng
#   RCEES
#   June 29, 2020
# Copyright (C) 2020  Qingyu Feng, RCEES

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# version 2, 1991 as published by the Free Software Foundation.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# A copy of the full GNU General Public License is included in file
# gpl.html. This is also available at:
# http://www.gnu.org/copyleft/gpl.html
# or from:
# The Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA  02111-1307, USA.

# If you wish to use or incorporate this program (or parts of it) into
# other software that does not meet the GNU General Public License
# conditions contact the author to request permission.
# Qingyu Feng
# email:  qyfeng18@rcees.ac.cn

import arcpy
from arcpy.sa import *
import sys, os, time
import subprocess
import matplotlib.pyplot as plt
import matplotlib
import json

arcpy.CheckOutExtension("Spatial")


class Toolbox(object):
    def __init__(self):
        self.label = "ArcpySSLMFP"
        self.alias  = "The Python Toolbox for Source Sink Landscape Erosion Model (SSLM)"

        # List of tool classes associated with this toolbox
        self.tools = [PitRemoveD8FlowDir,
                        DelineateStreamNet,
                        DelineateWatershed,
                        DisttoOltSubWS,
                        CalculateLorenzCurve,
                        PlotLorenzCurve,
                        CalSSLMErosionIdx
                        ] 


class PitRemoveD8FlowDir(object):
    def __init__(self):
        self.label       = "Step01_PitRemoveD8FlowDir"
        self.description = "This tool calls for the tools of PitRemove, " + \
                           " and D8FlowDirection.\n " + \
                           " Users need to provide at least: \n 1. a dem layer" + \
                           "to run this tool. Besides, users can provide:\n" + \
                           "2. number of processers: which require mpich installation"
                           
        self.canRunInBackground = False


    def getParameterInfo(self):
        #Define parameter definitions

        # Input raster parameter
        in_dem = arcpy.Parameter(
            displayName="Input DEM Raster",
            name="in_dem",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_noProc = arcpy.Parameter(
            displayName="Input number of processers (require mpiexec)",
            name="in_noProc",
            datatype="long",
            parameterType="Optional",
            direction="Input")

        in_noProc.value = 0

        # Output raster parameter
        out_fel = arcpy.Parameter(
            displayName="Output Filled DEM Raster (fel)",
            name="OutputFillDEM",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Output")

        # Output raster parameter
        out_sd8slope = arcpy.Parameter(
            displayName="Output D8 Slope (sd8)",
            name="out_sd8slope",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Output")

        # Output raster parameter
        out_pflowdir = arcpy.Parameter(
            displayName="Output D8 Flow Direction (pflowdir)",
            name="out_pflowdir",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Output")

        parameters = [in_dem,
                     in_noProc,
                     out_fel,
                     out_sd8slope,
                     out_pflowdir
                    ]
        
        return parameters            
        
        
    def updateParameters(self, parameters): #optional

        import os
        in_dem = parameters[0].valueAsText

        # Output Parameter 2 fel
        if in_dem and (not parameters[2].altered):
            if arcpy.Exists(in_dem):    
                desc = arcpy.Describe(in_dem)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[2].value=os.path.join(path, "fel."+ desc.extension)

        # Output Parameter 3 sd8slope
        if in_dem and (not parameters[3].altered):
            if arcpy.Exists(in_dem):    
                desc = arcpy.Describe(in_dem)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[3].value=os.path.join(path, "sd8slope."+ desc.extension)

        # Output Parameter 4 out_pflowdir
        if in_dem and (not parameters[4].altered):
            if arcpy.Exists(in_dem):    
                desc = arcpy.Describe(in_dem)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[4].value=os.path.join(path, "pflowdir."+ desc.extension)   

        return  
        
        

    def updateMessages(self, parameters): #optional
        return        
        
        
        
    def execute(self, parameters, messages):

        # Define parameters	          
        indem = parameters[0].valueAsText
        innoProc = parameters[1].valueAsText
        outfel = parameters[2].valueAsText
        outsd8slope = parameters[3].valueAsText
        outpflowdir = parameters[4].valueAsText

        # Set environments
        arcpy.env.extent = indem
        arcpy.env.snapRaster = indem
        rDesc = arcpy.Describe(indem)
        arcpy.env.cellSize = rDesc.meanCellHeight
        arcpy.env.overwriteOutput = True
        arcpy.env.scratchWorkspace = arcpy.env.scratchFolder
        arcpy.env.outputCoordinateSystem = indem

        if not arcpy.Exists(arcpy.env.workspace):
            arcpy.AddError("workspace does not exist!! Please set your workspace to a valid path directory in Arcmap --> Geoprocessing --> Environments --> Workspace")
            sys.exit(0)
            
        self.runPitRemoveD8FlowDir(indem, outfel,
                     outsd8slope,
                     outpflowdir, innoProc
                     )

    
    def runPitRemoveD8FlowDir(self, indem, out_fel,
                     out_sd8slope, out_pflowdir, numProcesses):
    
        # run pitremove
        arcpy.AddMessage("\nStep 1: Filling DEM with PitRemove")
        # Check existence of the input dem data
        if not arcpy.Exists(indem):
            arcpy.AddError("Error: input file \n{}\n does not exist!!".format(indem))
        else:
            taudemutil = taudemfuncs()
            taudemutil.runPitRemove(indem, out_fel, numProcesses)
        # Check the successfulness of the command by checking existence fo the output
        if arcpy.Exists(out_fel):
            arcpy.AddMessage("Output fel has been created successfully: \n{}!!".format(out_fel))
        else:
            arcpy.AddError("Error running the pit remove tool!!")

        time.sleep(1)

        # run d8flowdir
        arcpy.AddMessage("\n\nStep 2: Running D8FlowDir to generate flow direction and slope layers")
        taudemutil.runD8FlowDir(out_fel, out_sd8slope, out_pflowdir, numProcesses)
        # Check the successfulness of the command by checking existence fo the output
        if arcpy.Exists(out_sd8slope) and arcpy.Exists(out_pflowdir):
            arcpy.AddMessage("Output sd8slope \n{}\n and \n{}\nhas been created successfully!!".format(out_sd8slope, out_pflowdir))
        else:
            arcpy.AddError("Error running the d8flowdir tool!!")
            

class DelineateStreamNet(object):
    def __init__(self):
        self.label       = "Step02_DelineateStreamNet"
        self.description = "This tool calls for the tools of AreaD8, " + \
                           " and Threshold.\n " + \
                           " Users need to provide at least: \n 1. a dem layer" + \
                           "to run this tool. Besides, users can provide:\n" + \
                           "2. number of processers: which require mpich installation"
                           
        self.canRunInBackground = False


    def getParameterInfo(self):
        #Define parameter definitions

        # Input raster parameter
        in_pflowdir = arcpy.Parameter(
            displayName="Input D8 Flow Direction (pflowdir)",
            name="in_pflowdir",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_noProc = arcpy.Parameter(
            displayName="Input number of processers (require mpiexec)",
            name="in_noProc",
            datatype="long",
            parameterType="Optional",
            direction="Input")
        in_noProc.value = 0

        in_thresh = arcpy.Parameter(
            displayName="Threshold (for determining streams, unit: ha)",
            name="in_thresh",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")
        in_thresh.value = 9

        edge_cont = arcpy.Parameter(
            displayName="Check for edge contamination",
            name="edge_cont",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        edge_cont.value = True

        # Output raster parameter
        out_ad8 = arcpy.Parameter(
            displayName="Output D8 Contributing Area Grid (ad8)",
            name="out_ad8",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Output")

        # Output raster parameter
        out_strmnet = arcpy.Parameter(
            displayName="Output Stream Raster Grid (strmnet)",
            name="out_strmnet",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Output")



        parameters = [in_pflowdir,
                     in_noProc,
                     in_thresh,
                     edge_cont,
                     out_ad8,
                     out_strmnet
                    ]
        
        return parameters            
        
        
    def updateParameters(self, parameters): #optional

        import os
        in_pflowdir = parameters[0].valueAsText

        # Output Parameter 4 fel
        if in_pflowdir and (not parameters[4].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[4].value=os.path.join(path, "ad8."+ desc.extension)

        # Output Parameter 5 sd8slope
        if in_pflowdir and (not parameters[5].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[5].value=os.path.join(path, "strmnet."+ desc.extension)

        return  
        
        

    def updateMessages(self, parameters): #optional
        return        
        
        
    def execute(self, parameters, messages):

        # Define parameters	          
        inpflowdir = parameters[0].valueAsText
        innoProc = parameters[1].valueAsText
        inthresh = parameters[2].valueAsText
        edgecont = parameters[3].valueAsText
        outad8 = parameters[4].valueAsText
        outstrmnet = parameters[5].valueAsText

        # Set environments
        arcpy.env.extent = inpflowdir
        arcpy.env.snapRaster = inpflowdir
        rDesc = arcpy.Describe(inpflowdir)
        arcpy.env.cellSize = rDesc.meanCellHeight
        arcpy.env.overwriteOutput = True
        arcpy.env.scratchWorkspace = arcpy.env.scratchFolder
        arcpy.env.outputCoordinateSystem = inpflowdir

        if not arcpy.Exists(arcpy.env.workspace):
            arcpy.AddError("workspace does not exist!! Please set your workspace to a valid path directory in Arcmap --> Geoprocessing --> Environments --> Workspace")
            sys.exit(0)
            
        # get the cell height and width to get cell area
        cellw = rDesc.meanCellWidth
        cellh = rDesc.meanCellHeight
        cellarea = cellw * cellh
        inthresh = int(float(inthresh)* 10000.0/cellarea)

        self.runAreaD8Threshold(inpflowdir,
                     innoProc,
                     inthresh,
                     edgecont,
                     outad8,
                     outstrmnet
                     )

    
    def runAreaD8Threshold(self, inpflowdir, numProcesses, inthresh, edgecont,
                     outad8, outstrmnet):
    
        taudemutil = taudemfuncs()
        # run aread8
        arcpy.AddMessage("\nStep 1: Running aread8 to get flow accumulation")
        # Check existence of the input dem data
        if not arcpy.Exists(inpflowdir):
            arcpy.AddError("Error: input file \n{}\n does not exist!!".format(inpflowdir))
        else:
            taudemutil.runAreaD8(inpflowdir, outad8, None, None, numProcesses, edgecont)
        # Check the successfulness of the command by checking existence fo the output
        if arcpy.Exists(outad8):
            arcpy.AddMessage("Output fel has been created successfully: \n{}!!".format(outad8))
        else:
            arcpy.AddError("Error running the aread8 tool!!")

        time.sleep(0.5)

        # run threshold
        arcpy.AddMessage("\n\nStep 2: Running threshold to generate streamnetwork")
        taudemutil.runThreshold(outad8, outstrmnet, str(inthresh), numProcesses)
        # Check the successfulness of the command by checking existence fo the output
        if arcpy.Exists(outstrmnet):
            arcpy.AddMessage("Output streamnetwork \n{}\n has been created successfully!!".format(outstrmnet))
        else:
            arcpy.AddError("Error running the threshold tool!!")


class DelineateWatershed(object):
    def __init__(self):
        self.label       = "Step03_DelineateWatershed"
        self.description = "This tool calls for the tools of AreaD8, " + \
                           " and Threshold, and streamnet with an outlet"
                           
        self.canRunInBackground = False


    def getParameterInfo(self):
        #Define parameter definitions
        in_outlet = arcpy.Parameter(
            displayName="Input Watershed Outlet feature layer (.shp)",
            name="in_outlet",
            datatype="DEShapefile",
            parameterType="Required",
            direction="Input")

        in_pflowdir = arcpy.Parameter(
            displayName="Input D8 Flow Direction (pflowdir)",
            name="in_pflowdir",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_strmnet = arcpy.Parameter(
            displayName="Output Stream Raster Grid (strmnet)",
            name="in_strmnet",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_fel = arcpy.Parameter(
            displayName="Input Pit Filled Elevation grid (fel)",
            name="in_fel",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_noProc = arcpy.Parameter(
            displayName="Input number of processers (require mpiexec)",
            name="in_noProc",
            datatype="long",
            parameterType="Optional",
            direction="Input")
        in_noProc.value = 0

        in_thresh = arcpy.Parameter(
            displayName="Threshold (for determining streams, unit: ha)",
            name="in_thresh",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")
        in_thresh.value = 9

        edge_cont = arcpy.Parameter(
            displayName="Check for edge contamination",
            name="edge_cont",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        edge_cont.value = True

        in_maxdist = arcpy.Parameter(
            displayName="Maximum number of grid cells to traverse in moving outlet points",
            name="in_maxdist",
            datatype="Long",
            parameterType="Optional",
            direction="Input")
        in_maxdist.value = 50

        out_mvolt = arcpy.Parameter(
            displayName="Moved Outlet (mvolt)",
            name="out_mvolt",
            datatype="DEShapefile",
            parameterType="Required",
            direction="Output")

        out_ad8olt = arcpy.Parameter(
            displayName="Output D8 Contributing Area Grid for Outlet Provided (ad8)",
            name="out_ad8olt",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Output")

        out_strmnetolt = arcpy.Parameter(
            displayName="Output Stream Raster Grid for Outlet Provided (strmnet)",
            name="out_strmnetolt",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Output")

        out_ord = arcpy.Parameter(
            displayName="Output Stream Order Grid (ord)",
            name="out_ord",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Output")

        out_tree = arcpy.Parameter(
            displayName="Output Network Connectivity Tree (tree)",
            name="out_tree",
            datatype="DETextfile",
            parameterType="Required",
            direction="Output")

        out_coord = arcpy.Parameter(
            displayName="Output Network Coordinates (coord)",
            name="out_coord",
            datatype="DETextfile",
            parameterType="Required",
            direction="Output")

        out_strmshp = arcpy.Parameter(
            displayName="Output Stream Reach file (strmnet)",
            name="out_strmshp",
            datatype="DEShapefile",
            parameterType="Required",
            direction="Output")

        out_wsbdy = arcpy.Parameter(
            displayName="Output Watershed Grid (wsbdy)",
            name="out_wsbdy",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Output")

        parameters = [in_outlet,
                     in_pflowdir,
                     in_strmnet,
                     in_noProc,
                     in_thresh,
                     edge_cont,
                     in_maxdist,
                     out_mvolt,
                     out_ad8olt,
                     out_strmnetolt,
                     in_fel,
                     out_ord,
                     out_tree,
                     out_coord,
                     out_strmshp,
                     out_wsbdy
                    ]
        
        return parameters            
        
        
    def updateParameters(self, parameters): #optional

        import os

        in_pflowdir = parameters[1].valueAsText

        # Output Parameter 2 in_strmnet
        if in_pflowdir and (not parameters[2].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[2].value=os.path.join(path, "strmnet."+ desc.extension)

        # Output Parameter 7 out_mvolt
        if in_pflowdir and (not parameters[7].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[7].value=os.path.join(path, "mvolt.shp")

        # Output Parameter 8 out_ad8olt
        if in_pflowdir and (not parameters[8].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[8].value=os.path.join(path, "ad8olt."+ desc.extension)

        # Output Parameter 9 out_strmnetolt
        if in_pflowdir and (not parameters[9].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[9].value=os.path.join(path, "strmnetolt."+ desc.extension)

        # Output Parameter 10 in_fel
        if in_pflowdir and (not parameters[10].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[10].value=os.path.join(path, "fel."+ desc.extension)

        # Output Parameter 11 out_ord
        if in_pflowdir and (not parameters[11].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[11].value=os.path.join(path, "ord."+ desc.extension)

        # Output Parameter 12 out_tree
        if in_pflowdir and (not parameters[12].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[12].value=os.path.join(path, "tree.txt")

        # Output Parameter 13 out_coord
        if in_pflowdir and (not parameters[13].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[13].value=os.path.join(path, "coord.txt")

        # Output Parameter 14 out_coord
        if in_pflowdir and (not parameters[14].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[14].value=os.path.join(path, "stream.shp")

        # Output Parameter 15 outwsbdy
        if in_pflowdir and (not parameters[15].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[15].value=os.path.join(path, "wsbdy."+ desc.extension)

        return  
        

    def updateMessages(self, parameters): #optional
        return        
        
        
    def execute(self, parameters, messages):

        # Define parameters	          
        inoutlet = parameters[0].valueAsText
        inpflowdir = parameters[1].valueAsText
        instrmnet = parameters[2].valueAsText
        innoProc = parameters[3].valueAsText
        inthresh = parameters[4].valueAsText
        edgecont = parameters[5].valueAsText
        inmaxdist = parameters[6].valueAsText
        outmvolt = parameters[7].valueAsText
        outad8olt = parameters[8].valueAsText
        outstrmnetolt = parameters[9].valueAsText
        infel = parameters[10].valueAsText
        outord = parameters[11].valueAsText
        outtree = parameters[12].valueAsText
        outcoord = parameters[13].valueAsText
        outstrmshp = parameters[14].valueAsText
        outwsbdy = parameters[15].valueAsText

        # Set environments
        arcpy.env.extent = inpflowdir
        arcpy.env.snapRaster = inpflowdir
        rDesc = arcpy.Describe(inpflowdir)
        arcpy.env.cellSize = rDesc.meanCellHeight
        arcpy.env.overwriteOutput = True
        arcpy.env.scratchWorkspace = arcpy.env.scratchFolder
        arcpy.env.outputCoordinateSystem = inpflowdir

        if not arcpy.Exists(arcpy.env.workspace):
            arcpy.AddError("workspace does not exist!! Please set your workspace to a valid path directory in Arcmap --> Geoprocessing --> Environments --> Workspace")
            sys.exit(0)
            
        # get the cell height and width to get cell area
        cellw = rDesc.meanCellWidth
        cellh = rDesc.meanCellHeight
        cellarea = cellw * cellh
        inthresh = int(float(inthresh)* 10000.0/cellarea)

        self.runAreaD8ThresholdStreamNet(
                    inoutlet,
                    inpflowdir,
                    instrmnet,
                    innoProc,
                    inthresh,
                    edgecont,
                    inmaxdist,
                    outmvolt,
                    outad8olt,
                    outstrmnetolt,
                    infel,
                    outord,
                    outtree,
                    outcoord,
                    outstrmshp,
                    outwsbdy
                     )

    
    def runAreaD8ThresholdStreamNet(self, inoutlet,
                        inpflowdir,
                        instrmnet,
                        numProcesses,
                        inthresh,
                        edgecont,
                        inmaxdist,
                        outmvolt,
                        outad8olt,
                        outstrmnetolt,
                        infel,
                        outord,
                        outtree,
                        outcoord,
                        outstrmshp,
                        outwsbdy):
    
        taudemutil = taudemfuncs()
        # run moveOutlettoStream
        arcpy.AddMessage("\nStep 1: move outlet to streamnet line")
        # Check existence of the input dem data
        if not arcpy.Exists(inpflowdir):
            arcpy.AddError("Error: input file \n{}\n does not exist!!".format(inpflowdir))
        else:
            taudemutil.runMoveOutlets(inpflowdir, instrmnet, inoutlet, outmvolt, numProcesses, inmaxdist)
        # Check the successfulness of the command by checking existence fo the output
        if arcpy.Exists(outmvolt):
            arcpy.AddMessage("Output has been created successfully: \n{}!!".format(outmvolt))
        else:
            arcpy.AddError("Error running the moveOutlettoStream tool!!")

        time.sleep(0.5)

        # run aread8
        arcpy.AddMessage("\nStep 2: aread8 to get flow accumulation")
        # Check existence of the input dem data
        taudemutil.runAreaD8(inpflowdir, outad8olt, outmvolt, None, numProcesses, edgecont)
        # Check the successfulness of the command by checking existence fo the output
        if arcpy.Exists(outad8olt):
            arcpy.AddMessage("Output has been created successfully: \n{}!!".format(outad8olt))
        else:
            arcpy.AddError("Error running the aread8 tool!!")

        time.sleep(0.5)

        # run threshold
        arcpy.AddMessage("\n\nStep 3: Running threshold to generate streamnetwork")
        taudemutil.runThreshold(outad8olt, outstrmnetolt, str(inthresh), numProcesses)
        # Check the successfulness of the command by checking existence fo the output
        if arcpy.Exists(outstrmnetolt):
            arcpy.AddMessage("Output streamnetwork \n{}\n has been created successfully!!".format(outstrmnetolt))
        else:
            arcpy.AddError("Error running threshold tool!!")

        time.sleep(0.5)

        # run streamnet
        arcpy.AddMessage("\n\nStep 4: Running streamnet to generate watershed")
        taudemutil.runStreamNet(infel, inpflowdir, outad8olt, outstrmnetolt, outmvolt, outord, 
            outtree, outcoord, outstrmshp, outwsbdy, False, numProcesses)
        # Check the successfulness of the command by checking existence fo the output
        if arcpy.Exists(outwsbdy):
            arcpy.AddMessage("Output streamnetwork \n{}\n has been created successfully!!".format(outwsbdy))
        else:
            arcpy.AddError("Error running threshold tool!!")

        
class DisttoOltSubWS(object):
    def __init__(self):
        self.label       = "Step04_DisttoOltSubWS"
        self.description = "This tool calls for the tools of dist2subolt, " + \
                           " and dist2wsolt to calculate the distance of each cell" + \
                           " to the subarea outlet and the watershed outlet, respectively."
        self.canRunInBackground = False


    def getParameterInfo(self):
        #Define parameter definitions

        # Input raster parameter
        in_pflowdir = arcpy.Parameter(
            displayName="Input D8 Flow Direction (pflowdir)",
            name="in_pflowdir",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_strmnetolt = arcpy.Parameter(
            displayName="Input Stream Raster Grid for Outlet Provided (strmnet)",
            name="in_strmnetolt",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_wsbdy = arcpy.Parameter(
            displayName="Input Watershed Boundary Grid",
            name="in_wsbdy",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_noProc = arcpy.Parameter(
            displayName="Input number of processers (require mpiexec)",
            name="in_noProc",
            datatype="long",
            parameterType="Optional",
            direction="Input")
        in_noProc.value = 0

        out_dist2sub = arcpy.Parameter(
            displayName="Output D8 Distance to subarea outlet (dist2subolt)",
            name="out_dist2sub",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Output")

        out_dist2ws = arcpy.Parameter(
            displayName="Output D8 Distance to watershes outlet (dist2wsolt)",
            name="out_dist2ws",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Output")

        parameters = [
                    in_pflowdir,
                    in_strmnetolt,
                     in_wsbdy,
                     out_dist2sub,
                     out_dist2ws,
                     in_noProc
                    ]
        
        return parameters            
        
        
    def updateParameters(self, parameters): #optional

        import os

        in_pflowdir = parameters[0].valueAsText

        # Output Parameter 2 in_strmnet
        if in_pflowdir and (not parameters[1].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[1].value=os.path.join(path, "strmnetolt."+ desc.extension)

        # Output Parameter 2 in_wsbdy
        if in_pflowdir and (not parameters[2].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[2].value=os.path.join(path, "wsbdy."+ desc.extension)

        # Output Parameter 3 out_dist2ws
        if in_pflowdir and (not parameters[3].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[3].value=os.path.join(path, "dist2subolt."+ desc.extension)

        # Output Parameter 4 out_dist2sub
        if in_pflowdir and (not parameters[4].altered):
            if arcpy.Exists(in_pflowdir):    
                desc = arcpy.Describe(in_pflowdir)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[4].value=os.path.join(path, "dist2wsolt."+ desc.extension)

        return  
        
        

    def updateMessages(self, parameters): #optional
        return        
        
        
    def execute(self, parameters, messages):

        # Define parameters	          
        inpflowdir = parameters[0].valueAsText
        instrmnetolt = parameters[1].valueAsText
        inwsbdy = parameters[2].valueAsText
        outdist2sub = parameters[3].valueAsText
        outdist2ws = parameters[4].valueAsText                  
        in_noProc =  parameters[5].valueAsText

        # Set environments
        arcpy.env.extent = inpflowdir
        arcpy.env.snapRaster = inpflowdir
        rDesc = arcpy.Describe(inpflowdir)
        arcpy.env.cellSize = rDesc.meanCellHeight
        arcpy.env.overwriteOutput = True
        arcpy.env.scratchWorkspace = arcpy.env.scratchFolder
        arcpy.env.outputCoordinateSystem = inpflowdir

        if not arcpy.Exists(arcpy.env.workspace):
            arcpy.AddError("workspace does not exist!! Please set your workspace to a valid path directory in Arcmap --> Geoprocessing --> Environments --> Workspace")
            sys.exit(0)

        self.runDist2SubWsOlt(
                    inpflowdir, 
                    instrmnetolt,
                    inwsbdy,
                    outdist2sub,
                    outdist2ws,
                    in_noProc)

    
    def runDist2SubWsOlt(self, 
                    inpflowdir, 
                    instrmnetolt,
                    inwsbdy,
                    outdist2sub,
                    outdist2ws,
                    numProcesses):
    
        taudemutil = taudemfuncs()
        # run dist2subolt
        arcpy.AddMessage("\nStep 1: Distance to subarea outlet")
        # Check existence of the input dem data
        if not arcpy.Exists(inpflowdir):
            arcpy.AddError("Error: input file \n{}\n does not exist!!".format(inpflowdir))
        else:
            taudemutil.runDist2SubOlt(inpflowdir, inwsbdy, instrmnetolt, outdist2sub, numProcesses)
        # Check the successfulness of the command by checking existence fo the output
        if arcpy.Exists(outdist2sub):
            arcpy.AddMessage("Output has been created successfully: \n{}!!".format(outdist2sub))
        else:
            arcpy.AddError("Error running the dist2subolt tool!!")

        time.sleep(0.5)

        # run dist2wsolt
        arcpy.AddMessage("\nStep 2: Distance to watershed outlet")
        taudemutil.runDist2WsOlt(inpflowdir, instrmnetolt, outdist2ws, numProcesses)
        # Check the successfulness of the command by checking existence fo the output
        if arcpy.Exists(outdist2ws):
            arcpy.AddMessage("Output has been created successfully: \n{}!!".format(outdist2ws))
        else:
            arcpy.AddError("Error running the dist2wsolt tool!!")


class CalculateLorenzCurve(object):
    def __init__(self):
        self.label       = "Step05_CalculateLorenzCurve"
        self.description = "This tool clips the land use with the watershed boundary, " + \
                           " calls for two c++ program to calculate the lorenz curve.\n " + \
                           " Users need to provide: \n 1. a landuse layer" + \
                           "to run this tool. Besides, users can provide:\n" + \
                           "2. number of processers: which require mpich installation"
                           
        self.canRunInBackground = False


    def getParameterInfo(self):
        #Define parameter definitions

        # Input raster parameter
        in_lu = arcpy.Parameter(
            displayName="Input Landuse Raster",
            name="in_lu",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_fel = arcpy.Parameter(
            displayName="Input Pit Removed Elevation Grid (fel)",
            name="in_fel",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_pflowdir = arcpy.Parameter(
            displayName="Input D8 Flow Direction (pflowdir)",
            name="in_pflowdir",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_wsbdy = arcpy.Parameter(
            displayName="Input Watershed boundary (wsbdy)",
            name="in_wsbdy",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_sd8 = arcpy.Parameter(
            displayName="Input D8 Slope (sd8)",
            name="in_sd8",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_noProc = arcpy.Parameter(
            displayName="Input number of processers (require mpiexec)",
            name="in_noProc",
            datatype="long",
            parameterType="Optional",
            direction="Input")
        in_noProc.value = 0

        in_dist2sub = arcpy.Parameter(
            displayName="Input D8 Distance to subarea outlet (dist2subolt)",
            name="out_dist2sub",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_dist2ws = arcpy.Parameter(
            displayName="Input D8 Distance to watershes outlet (dist2wsolt)",
            name="out_dist2ws",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")
        
        out_luwsext = arcpy.Parameter(
            displayName="Output Land use Clipped to Watershed boundary",
            name="out_luwsext",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output")

        out_lzsubjson = arcpy.Parameter(
            displayName="Output JSON file for subarea lorenz curve and area",
            name="out_lzsubjson",
            datatype="DEFile",
            parameterType="Required",
            direction="Output")

        out_lzwsjson = arcpy.Parameter(
            displayName="Output JSON file for watershed lorenz curve and area",
            name="out_lzwsjson",
            datatype="DEFile",
            parameterType="Required",
            direction="Output")

        parameters = [in_lu,
                     in_fel,
                     in_pflowdir,
                     in_wsbdy,
                     in_sd8,
                     in_dist2sub,
                     in_dist2ws,
                     out_luwsext,
                     out_lzsubjson,
                     out_lzwsjson,
                     in_noProc
                    ]
        
        return parameters            
        
        
    def updateParameters(self, parameters): #optional

        import os
        in_fel = parameters[1].valueAsText

        # Input Parameter 2 in_pflowdir
        if in_fel and (not parameters[2].altered):
            if arcpy.Exists(in_fel):    
                desc = arcpy.Describe(in_fel)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[2].value=os.path.join(path, "pflowdir."+ desc.extension)

        # Input Parameter 3 in_wsbdy
        if in_fel and (not parameters[3].altered):
            if arcpy.Exists(in_fel):    
                desc = arcpy.Describe(in_fel)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[3].value=os.path.join(path, "wsbdy."+ desc.extension)

        # Input Parameter 4 in_sd8
        if in_fel and (not parameters[4].altered):
            if arcpy.Exists(in_fel):    
                desc = arcpy.Describe(in_fel)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[4].value=os.path.join(path, "sd8slope."+ desc.extension)

        # Input Parameter 5 in_dist2sub
        if in_fel and (not parameters[5].altered):
            if arcpy.Exists(in_fel):    
                desc = arcpy.Describe(in_fel)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[5].value=os.path.join(path, "dist2subolt."+ desc.extension)

        # Input Parameter 6 in_dist2ws
        if in_fel and (not parameters[6].altered):
            if arcpy.Exists(in_fel):    
                desc = arcpy.Describe(in_fel)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[6].value=os.path.join(path, "dist2wsolt."+ desc.extension)

        # Input Parameter 7 out_luwsext
        if in_fel and (not parameters[7].altered):
            if arcpy.Exists(in_fel):    
                desc = arcpy.Describe(in_fel)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[7].value=os.path.join(path, "luWsExt."+ desc.extension)

        # Input Parameter 8 out_lzsubjson
        if in_fel and (not parameters[8].altered):
            if arcpy.Exists(in_fel):    
                desc = arcpy.Describe(in_fel)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[8].value=os.path.join(path, "lzsub.json")

        # Input Parameter 9 out_lzwsjson
        if in_fel and (not parameters[9].altered):
            if arcpy.Exists(in_fel):    
                desc = arcpy.Describe(in_fel)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[9].value=os.path.join(path, "lzws.json")

        return  
        
        

    def updateMessages(self, parameters): #optional
        return        
        
        
    def execute(self, parameters, messages):

        # Define parameters	          
        inlu = parameters[0].valueAsText
        infel = parameters[1].valueAsText
        inpflowdir = parameters[2].valueAsText
        inwsbdy = parameters[3].valueAsText
        insd8 = parameters[4].valueAsText
        indist2sub = parameters[5].valueAsText
        indist2ws = parameters[6].valueAsText
        outluwsext = parameters[7].valueAsText
        outlzsubjson = parameters[8].valueAsText
        outlzwsjson = parameters[9].valueAsText
        innoProc = parameters[10].valueAsText

        # Set environments
        arcpy.env.extent = infel
        arcpy.env.snapRaster = infel
        rDesc = arcpy.Describe(infel)
        arcpy.env.cellSize = rDesc.meanCellHeight
        arcpy.env.overwriteOutput = True
        arcpy.env.scratchWorkspace = arcpy.env.scratchFolder
        arcpy.env.outputCoordinateSystem = infel

        if not arcpy.Exists(arcpy.env.workspace):
            arcpy.AddError("workspace does not exist!! Please set your workspace to a valid path directory in Arcmap --> Geoprocessing --> Environments --> Workspace")
            sys.exit(0)
            
        self.runLorenzCurve(        
                    inlu,
                     infel,
                     inpflowdir,
                     inwsbdy,
                     insd8,
                     indist2sub,
                     indist2ws,
                     outluwsext,
                     outlzsubjson,
                     outlzwsjson,
                     innoProc
                     )

    def runLorenzCurve(self,         
                    inlu,
                     infel,
                     inpflowdir,
                     inwsbdy,
                     insd8,
                     indist2sub,
                     indist2ws,
                     outluwsext,
                     outlzsubjson,
                     outlzwsjson,
                     numProcesses):
    
        # Execute ExtractByMask
        arcpy.AddMessage("\nStep 1: Extracting Landuse!!!")
        # Check existence of the input dem data
        if not arcpy.Exists(inlu):
            arcpy.AddError("Error: input file \n{}\n does not exist!!".format(inlu))
        else:
            # Delete outfile if exists
            if arcpy.Exists(outluwsext):
                arcpy.Delete_management(outluwsext)
            outLuWatershed = ExtractByMask(inlu, inwsbdy)
            # Save the output 
            outLuWatershed.save(outluwsext)
            #arcpy.BuildPyramids_management(outluwsext)
        
        time.sleep(0.5)

        # run runsslmfpsub
        arcpy.AddMessage("\nStep 2: Running lurenzfpsub")
        # Check existence of the input dem data
        if not arcpy.Exists(inpflowdir):
            arcpy.AddError("Error: input file \n{}\n does not exist!!".format(inpflowdir))
        else:
            taudemutil = taudemfuncs()
            taudemutil.runlurenzfpsub(inpflowdir, indist2sub,
                                     inwsbdy, outluwsext,
                                     infel, insd8, outlzsubjson,
                                     numProcesses)
        # Check the successfulness of the command by checking existence fo the output
        if os.path.exists(outlzsubjson):
            arcpy.AddMessage("Output has been created successfully: \n{}!!".format(outlzsubjson))
        else:
            arcpy.AddError("Error running the lurenzfpsub tool!!")

        time.sleep(0.5)

        # run lurenzfpws
        arcpy.AddMessage("\nStep 3: Running lurenzfpws")
        # Check existence of the input dem data
        taudemutil = taudemfuncs()
        taudemutil.runlorenzfpws(inpflowdir, indist2ws,
                                     inwsbdy, outluwsext,
                                     infel, insd8, outlzwsjson,
                                     numProcesses)
        # Check the successfulness of the command by checking existence fo the output
        if os.path.exists(outlzwsjson):
            arcpy.AddMessage("Output has been created successfully: \n{}!!".format(outlzwsjson))
        else:
            arcpy.AddError("Error running the lurenzfpws tool!!")


class PlotLorenzCurve(object):
    def __init__(self):
        self.label       = "Step06_PlotLorenzCurve"
        self.description = "This tool creates the lorenz plot for watershed and subareas." 
                           
        self.canRunInBackground = False


    def getParameterInfo(self):

        in_lzwsjson = arcpy.Parameter(
            displayName="Input JSON file for watershed Lorenz curve and area (lzws.json)",
            name="in_lzwsjson",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")

        # Output raster parameter
        out_elevfigws = arcpy.Parameter(
            displayName="Output figure file name for elevation of watershed",
            name="out_elevfigws",
            datatype="GPString",
            parameterType="Required",
            direction="Output")       
            
        # Output raster parameter
        out_distfigws = arcpy.Parameter(
            displayName="Output figure file name for distance of watershed",
            name="out_distfigws",
            datatype="GPString",
            parameterType="Required",
            direction="Output")          
        
        out_slpfigws = arcpy.Parameter(
            displayName="Output figure file name for slope of watershed",
            name="out_slpfigws",
            datatype="GPString",
            parameterType="Required",
            direction="Output") 

        gen_subfig = arcpy.Parameter(
            displayName="Generate figures for subarea",
            name="gen_subfig",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        gen_subfig.value = False

        in_lzsubjson = arcpy.Parameter(
            displayName="Input JSON file for subarea Lorenz curve and area (lzsub.json)",
            name="in_lzsubjson",
            datatype="DEFile",
            parameterType="Optional",
            direction="Input")

        # Output raster parameter
        out_fdfigsub = arcpy.Parameter(
            displayName="Output folder to store subarea figures",
            name="out_fdfigsub",
            datatype="GPString",
            parameterType="Optional",
            direction="Output")       

        parameters = [in_lzwsjson,
                     out_elevfigws,
                     out_distfigws,
                     out_slpfigws,
                     gen_subfig,
                     in_lzsubjson,
                     out_fdfigsub
                    ]
        
        return parameters            
        
        
    def updateParameters(self, parameters): #optional

        import os
        in_lzwsjson = parameters[0].valueAsText

        # Output Parameter 1: out_elevfigws figure name
        if in_lzwsjson and (not parameters[1].altered):
            if arcpy.Exists(in_lzwsjson):    
                desc = arcpy.Describe(in_lzwsjson)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[1].value=os.path.join(path, "lzelevws.png")
        
        # Output Parameter 2: out_distfigws figure name
        if in_lzwsjson and (not parameters[2].altered):
            if arcpy.Exists(in_lzwsjson):    
                desc = arcpy.Describe(in_lzwsjson)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[2].value=os.path.join(path, "lzdistws.png")

        # Output Parameter 3: out_slpfigws figure name
        if in_lzwsjson and (not parameters[3].altered):
            if arcpy.Exists(in_lzwsjson):    
                desc = arcpy.Describe(in_lzwsjson)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[3].value=os.path.join(path, "lzslpws.png")        
            
        gen_SubFigflag = parameters[4].value
        # In Parameter 5: lzjsonsub
        if gen_SubFigflag and (not parameters[5].altered):
            if arcpy.Exists(in_lzwsjson):    
                desc = arcpy.Describe(in_lzwsjson)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[5].value=os.path.join(path, "lzsub.json")   

        
        # Output Parameter 6: output folder for sub figures
        if gen_SubFigflag and (not parameters[6].altered):
            if arcpy.Exists(in_lzwsjson):    
                desc = arcpy.Describe(in_lzwsjson)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[6].value=os.path.join(path, "subfigures")

        return  
        
        

    def updateMessages(self, parameters): #optional
        return        
        
        
        
    def execute(self, parameters, messages):

        # Define parameters	          
        inlzwsjson = parameters[0].valueAsText
        outelevfigws = parameters[1].valueAsText
        outdistfigws = parameters[2].valueAsText
        outslpfigws = parameters[3].valueAsText
        gensubfig = parameters[4].valueAsText
        inlzsubjson = parameters[5].valueAsText
        outfdfigsub = parameters[6].valueAsText

                    

        self.runPlotLorenzWsSub(        
                     inlzwsjson,
                     outelevfigws,
                     outdistfigws,
                     outslpfigws,
                     gensubfig,
                     inlzsubjson,
                     outfdfigsub
                     )

    def runPlotLorenzWsSub(self,         
                     inlzwsjson,
                     outelevfigws,
                     outdistfigws,
                     outslpfigws,
                     gensubfig,
                     inlzsubjson,
                     outfdfigsub):
    
        # From here, we need to get the modules in another class
        # Create instance of class

        # Here, the AppLorenzCurve class need to be initalized 
        # for making curves of LorenzCurve from the LWLI data.
        import os
        plotLZApp = LzplotUtil()

        lzwsjson = plotLZApp.readJSON(inlzwsjson)
        distkeyws = "Dist2WSOlt"
        plotLZApp.plotWS(lzwsjson, outelevfigws, outdistfigws, outslpfigws, distkeyws)

        
        if gensubfig == "true":
            if not os.path.isdir(outfdfigsub):
                os.mkdir(outfdfigsub)
            elif os.path.isdir(outfdfigsub):
                os.removedirs(outfdfigsub)
                os.mkdir(outfdfigsub)
            
            lzsubjson = plotLZApp.readJSON(inlzsubjson)
            plotLZApp.plotSub(lzsubjson, outfdfigsub)


class CalSSLMErosionIdx(object):
    def __init__(self):
        self.label       = "Step07_CalSSLMErosionIndex"
        self.description = "This tool creates the SSLM Erosion Index for watershed and subareas." 
                           
        self.canRunInBackground = False


    def getParameterInfo(self):

        in_lzwsjson = arcpy.Parameter(
            displayName="Input JSON file for watershed Lorenz curve and area (lzws.json)",
            name="in_lzwsjson",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")

        in_lzsubjson = arcpy.Parameter(
            displayName="Input JSON file for subarea Lorenz curve and area (lzsub.json)",
            name="in_lzsubjson",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")

        in_srcwgt = arcpy.Parameter(
            displayName="Input text file containing weights for source landuses",
            name="in_srcwgt",
            datatype="DETextfile",
            parameterType="Required",
            direction="Input")             
                      
        in_sinkwgt = arcpy.Parameter(
            displayName="Input text file containing weights for sink landuses",
            name="in_sinkwgt",
            datatype="DETextfile",
            parameterType="Required",
            direction="Input")         

        in_wsbdy = arcpy.Parameter(
            displayName="Input Watershed Boundary Grid",
            name="in_wsbdy",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        out_idxws = arcpy.Parameter(
            displayName="Output file containing index values for watershed",
            name="out_idxws",
            datatype="GPString",
            parameterType="Required",
            direction="Output")       

        out_idxsub = arcpy.Parameter(
            displayName="Output file containing index values for subarea",
            name="out_idxsub",
            datatype="GPString",
            parameterType="Required",
            direction="Output")

        out_subidxgrid = arcpy.Parameter(
            displayName="Ouput Subarea SSLM Erosion Index Grid",
            name="out_subidxgrid",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Output")

        parameters = [in_lzwsjson,
                     in_lzsubjson,
                     in_srcwgt,
                     in_sinkwgt,
                     in_wsbdy,
                     out_idxws,
                     out_idxsub,
                    out_subidxgrid
                    ]
        
        return parameters            
        
        
    def updateParameters(self, parameters): #optional

        import os
        in_lzwsjson = parameters[0].valueAsText

        # Input Parameter 1: lzjsonsub
        if in_lzwsjson and (not parameters[1].altered):
            if arcpy.Exists(in_lzwsjson):    
                desc = arcpy.Describe(in_lzwsjson)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[1].value=os.path.join(path, "lzsub.json")   

        # Input Parameter 2: srclus_withweights
        if in_lzwsjson and (not parameters[2].altered):
            if arcpy.Exists(in_lzwsjson):    
                desc = arcpy.Describe(in_lzwsjson)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[2].value=os.path.join(path, "srclus_withweights.json")
        
        # Input Parameter 3: sinklus_withweights
        if in_lzwsjson and (not parameters[3].altered):
            if arcpy.Exists(in_lzwsjson):    
                desc = arcpy.Describe(in_lzwsjson)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[3].value=os.path.join(path, "sinklus_withweights.json")
        
        # Input Parameter 4: in_wsbdy
        if in_lzwsjson and (not parameters[4].altered):
            if arcpy.Exists(in_lzwsjson):    
                desc = arcpy.Describe(in_lzwsjson)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[4].value=os.path.join(path, "wsbdy.tif")

        # Output Parameter 5: out_idxws
        if in_lzwsjson and (not parameters[5].altered):
            if arcpy.Exists(in_lzwsjson):    
                desc = arcpy.Describe(in_lzwsjson)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[5].value=os.path.join(path, "sslmidxforws.json")        

        # Output Parameter 6: out_idxsub
        if in_lzwsjson and (not parameters[6].altered):
            if arcpy.Exists(in_lzwsjson):    
                desc = arcpy.Describe(in_lzwsjson)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[6].value=os.path.join(path, "sslmidxforsub.json")     

        # Output Parameter 7: out_subidxgrid
        if in_lzwsjson and (not parameters[7].altered):
            if arcpy.Exists(in_lzwsjson):    
                desc = arcpy.Describe(in_lzwsjson)
                infile=str(desc.catalogPath) 
                path,filename = os.path.split(infile)
                parameters[7].value=os.path.join(path, "suberoidx.tif")     

        return  
        
        

    def updateMessages(self, parameters): #optional
        return        
        
        
        
    def execute(self, parameters, messages):

        # Define parameters	          
        inlzwsjson = parameters[0].valueAsText
        inlzsubjson = parameters[1].valueAsText
        insrcwgt = parameters[2].valueAsText
        insinkwgt = parameters[3].valueAsText
        inwsbdy = parameters[4].valueAsText
        outidxws = parameters[5].valueAsText
        outidxsub = parameters[6].valueAsText
        outsubidxgrid = parameters[7].valueAsText

        # Set environments
        arcpy.env.extent = inwsbdy
        arcpy.env.snapRaster = inwsbdy
        rDesc = arcpy.Describe(inwsbdy)
        arcpy.env.cellSize = rDesc.meanCellHeight
        arcpy.env.overwriteOutput = True
        arcpy.env.scratchWorkspace = arcpy.env.scratchFolder
        arcpy.env.outputCoordinateSystem = inwsbdy

        if not arcpy.Exists(arcpy.env.workspace):
            arcpy.AddError("workspace does not exist!! Please set your workspace to a valid path directory in Arcmap --> Geoprocessing --> Environments --> Workspace")
            sys.exit(0)

        self.runCalSSLMIdx(        
                     inlzwsjson,
                     inlzsubjson,
                     insrcwgt,
                     insinkwgt,
                     inwsbdy,
                     outidxws,
                     outidxsub,
                    outsubidxgrid
                     )

    def runCalSSLMIdx(self,         
                     inlzwsjson,
                     inlzsubjson,
                     insrcwgt,
                     insinkwgt,
                     inwsbdy,
                     outidxws,
                     outidxsub,
                     outsubidxgrid):
 
        arcpy.AddMessage("Step 1: Calculate the sslmfidx for watershed")

        calWSIdx = calSSLMWS()
        srckLuWgts = calWSIdx.readJSON(insrcwgt)["Sourcelu_Weights"]
        sinkLuWgts = calWSIdx.readJSON(insinkwgt)["Sinklu_Weights"]
        lzwsjs = calWSIdx.readJSON(inlzwsjson)
        SinkProd = calWSIdx.calcProdLzAWgtPerA(lzwsjs, sinkLuWgts)
        SrcProd = calWSIdx.calcProdLzAWgtPerA(lzwsjs,  srckLuWgts)
        sslmIndex = calWSIdx.calcSslmIndex(SrcProd, SinkProd)
        with open(outidxws, 'w') as json_file:
           json.dump(sslmIndex, json_file)

        del(calWSIdx)
        del(lzwsjs)
        del(SinkProd)
        del(SrcProd)
        del(sslmIndex)
        
        arcpy.AddMessage("Step 2: Calculate the sslmfidx for subarea")        
        calSubIdx = calSSLMSub()
        srckLuWgts = calSubIdx.readJSON(insrcwgt)["Sourcelu_Weights"]
        sinkLuWgts = calSubIdx.readJSON(insinkwgt)["Sinklu_Weights"]
        lzsubjs = calSubIdx.readJSON(inlzsubjson)
        SinkProdAllsubs = calSubIdx.calcProdLzAWgtPerASubs(lzsubjs, sinkLuWgts)
        SrcProdAllsubs = calSubIdx.calcProdLzAWgtPerASubs(lzsubjs, srckLuWgts)
        sslmIndex = calSubIdx.calcSslmIndexSubs(SinkProdAllsubs, SrcProdAllsubs)
        with open(outidxsub, 'w') as json_file:
           json.dump(sslmIndex, json_file)

        time.sleep(0.5)

        arcpy.AddMessage("Step 3: Generating subarea sslm erosion index map")  
        arcpy.AddMessage("\nStep 3: running subindexmap")
        # Check existence of the input dem data
        taudemutil = taudemfuncs()
        # runsubindexmap(self, wfile, inSubJson, outSslmSub, numProcesses)
        taudemutil.runsubindexmap(inwsbdy, outidxsub, outsubidxgrid, "0")
        # Check the successfulness of the command by checking existence fo the output
        if os.path.exists(outsubidxgrid):
            arcpy.AddMessage("Output has been created successfully: \n{}!!".format(outsubidxgrid))
        else:
            arcpy.AddError("Error running the subindexmap tool!!")


class calSSLMSub(object):

    def calcSslmIndexSubs(self, SinkProdAllsubs, SrcProdAllsubs):
        
        prodDictSubs = {}

        for subno in SinkProdAllsubs.keys():
            print("subno: ", subno)
            prodDictSubs[subno] = self.calcSslmIndex(SrcProdAllsubs[subno], SinkProdAllsubs[subno])

        return prodDictSubs



    def calcProdLzAWgtPerASubs(self, lzsubjs, LuWgts):
        
        prodDictSubs = {}

        for k, v in lzsubjs.items():
            prodDictSubs[k] = self.calcProdLzAWgtPerA(v, LuWgts)

            #print(prodDictSubs[k])
        return prodDictSubs


    def calcSslmIndex(self,  SrcProd, SinkProd):

        # In each value of SrcProd and SinkProd,
        # it has elevation, distance, and slope
        srcSum = [0, 0, 0]
        for varid in range(3):
            for k, v in SrcProd.items():
                print("Src:",k,v)
                srcSum[varid] = srcSum[varid] + v[varid]

        sinkSum = [0, 0, 0]
        for varid in range(3):
            for k, v in SinkProd.items():
                print("sink:",k,v)
                sinkSum[varid] = sinkSum[varid] + v[varid]

        # Output the file injson format
        # To avoid the error divid by 0
        if ((srcSum[0] + sinkSum[0]) == 0.0):
            elevSSLM = 0.0
        else: 
            elevSSLM = srcSum[0]/(srcSum[0] + sinkSum[0])

        if ((srcSum[1] + sinkSum[1]) == 0.0):
            distSSLM = 0.0
        else: 
            distSSLM = srcSum[1]/(srcSum[1] + sinkSum[1])
        
        if ((srcSum[2] + sinkSum[2]) == 0.0):
            slopeSSLM = 0.0
        else: 
            slopeSSLM = srcSum[2]/(srcSum[2] + sinkSum[2])

        if (slopeSSLM == 0.0):
            combSSLM = 0.0
        else:
            combSSLM = elevSSLM*distSSLM/slopeSSLM

        outdict = {}
        outdict["elev"] = "{:.4f}".format(elevSSLM)
        outdict["dist"] = "{:.4f}".format(distSSLM)
        outdict["slp"] = "{:.4f}".format(slopeSSLM)
        outdict["comb"] = "{:.4f}".format(combSSLM)

        return outdict



    def calcProdLzAWgtPerA(self, 
                lzwsjs,
                sinkLuWgts):

        prodDict = {}

        # The original structure is lzCvArea = {lu: elevLzZrea, 
        # distLzArea and slope}  
        lzCvArea = {}

        # The original area percentage structure is:
        # luAreaPer  = {Lu: Area}
        luAreaPer = {}

        for kwj, vwj in lzwsjs.items():
            if not (kwj == "TotalSubArea"):
                lzCvArea[kwj] = list(map(float, [
                        vwj["LULZAreas"]["lzAreaElevation"],
                        vwj["LULZAreas"]["lzAreaDistance"],
                        vwj["LULZAreas"]["lzAreaSlope"]
                    ]))
                luAreaPer[kwj] = float(vwj["LULZAreas"]["totalLuAreaPer"])
                #print("LuNo: .." , kwj,"LuNo: .." , kwj, "...........", lzCvArea[kwj], luAreaPer[kwj])
                
        for k, v in sinkLuWgts.items(): 
            if k in luAreaPer.keys():
                prodDict[k] = [x*luAreaPer[k]*v for x in lzCvArea[k]]
                #print("LuNo: .." , k, "...........", lzCvArea[k], luAreaPer[k], prodDict[k])
                #print(prodDict[k])
            #print(luAreaPer[k], type(luAreaPer[k]), v, type(v))
            #*luAreaPer[k]*v

        return prodDict


    def readJSON(self, jsonname):
        
        inf_usrjson = 0
        
        with open(jsonname) as json_file:    
            inf_usrjson = json.loads(json_file.read())
    #        pprint.pprint(inf_usrjson)
        json_file.close()
        
        return inf_usrjson


class calSSLMWS(object):

    def calcSslmIndex(self,  SrcProd, SinkProd):
        # In each value of SrcProd and SinkProd,
        # it has elevation, distance, and slope
        srcSum = [0, 0, 0]
        for varid in range(3):
            for k, v in SrcProd.items():
                srcSum[varid] = srcSum[varid] + v[varid]

        sinkSum = [0, 0, 0]
        for varid in range(3):
            for k, v in SinkProd.items():
                sinkSum[varid] = sinkSum[varid] + v[varid]

        # Output the file injson format
        if ((srcSum[0] + sinkSum[0]) == 0.0):
            elevSSLM = 0.0
        else: 
            elevSSLM = srcSum[0]/(srcSum[0] + sinkSum[0])

        if ((srcSum[1] + sinkSum[1]) == 0.0):
            distSSLM = 0.0
        else: 
            distSSLM = srcSum[1]/(srcSum[1] + sinkSum[1])
        
        if ((srcSum[2] + sinkSum[2]) == 0.0):
            slopeSSLM = 0.0
        else: 
            slopeSSLM = srcSum[2]/(srcSum[2] + sinkSum[2])

        if (slopeSSLM == 0.0):
            combSSLM = 0.0
        else:
            combSSLM = elevSSLM*distSSLM/slopeSSLM

        outdict = {}
        outdict["elev"] = "{:.4f}".format(elevSSLM)
        outdict["dist"] = "{:.4f}".format(distSSLM)
        outdict["slp"] = "{:.4f}".format(slopeSSLM)
        outdict["comb"] = "{:.4f}".format(combSSLM)

        return outdict

    def calcProdLzAWgtPerA(self, 
                lzwsjs,
                sinkLuWgts):

        prodDict = {}

        # The original structure is lzCvArea = {lu: elevLzZrea, 
        # distLzArea and slope}  
        lzCvArea = {}

        # The original area percentage structure is:
        # luAreaPer  = {Lu: Area}
        luAreaPer = {}

        for kwj, vwj in lzwsjs.items():
            lzCvArea[kwj] = list(map(float, [
                    vwj["LULZAreas"]["lzAreaElevation"],
                    vwj["LULZAreas"]["lzAreaDistance"],
                    vwj["LULZAreas"]["lzAreaSlope"]
                ]))
            luAreaPer[kwj] = float(vwj["LULZAreas"]["totalLuAreaPer"])

        for k, v in sinkLuWgts.items():   
            prodDict[k] = [x*luAreaPer[k]*v for x in lzCvArea[k]]

        return prodDict


    def readJSON(self, jsonname):
        
        inf_usrjson = 0
        with open(jsonname) as json_file:    
            inf_usrjson = json.loads(json_file.read(), encoding='utf-8')
    #        pprint.pprint(inf_usrjson)
        json_file.close()
        
        return inf_usrjson


class LzplotUtil(object):

    def readJSON(self, jsonname):
        inf_usrjson = 0
        with open(jsonname) as json_file:    
            inf_usrjson = json.loads(json_file.read(), encoding='utf-8')
    #        pprint.pprint(inf_usrjson)
        json_file.close()

        return inf_usrjson


    def plotSub(self, lzsubjson, outfdfigsub):

        subNoLst = list(lzsubjson.keys())
        distkeysub = "Dist2SubOlt"

        for subNo in subNoLst:
            arcpy.AddMessage("Creating figures for subarea: {}".format(subNo))
            sublzjs = None
            sublzjs = lzsubjson[subNo]
            subfigelev = os.path.join(outfdfigsub, "elevofSub{}.jpg".format(subNo))
            subfigdist = os.path.join(outfdfigsub, "distofSub{}".format(subNo))
            subfigslp = os.path.join(outfdfigsub, "distofSub{}".format(subNo))

            self.plotWS(sublzjs, subfigelev, subfigdist, subfigslp, distkeysub)
        

    def plotWS(self, wslzjs, fig_elev, fig_dist, fig_slp, distkey):
            #plotLZApp.plotOneSub("ws", lzwsjson, 
            #pltfig, 0, 1, 3, "Dist2WSOlt"
            #)
        # Read the value from the text files containing the 
        # value and percentage for elevation.
        lulist = list(wslzjs.keys())

        #need to be reformated.
        elevFigDtPer = []
        distFigDtPer = []
        slpFigDtPer = []
        elevFigDtVal = []
        distFigDtVal = []
        slpFigDtVal = []

        # Also get the maximum and minimum value for each variable
        maxElev = []
        maxDist = []
        maxSlp = []
        minElev = []
        minDist = []
        minSlp = []

        max_elev = 0
        max_dist = 0
        max_slp = 0
        min_elev = 0
        min_dist = 0
        min_slp = 0

        for luidx in lulist:

            if luidx != "TotalSubArea":
                # Elevation
                elevV1lu = map(float, wslzjs[luidx]["Elevation"]["Value"])
                elevP1lu = map(float, wslzjs[luidx]["Elevation"]["Percent"])
                elevFigDtVal.append(elevV1lu)
                elevFigDtPer.append(elevP1lu)

                maxElev.append(max(elevV1lu))
                minElev.append(min(elevV1lu))

                # Dist
                distV1lu = map(float, wslzjs[luidx][distkey]["Value"])
                distP1lu = map(float, wslzjs[luidx][distkey]["Percent"])
                distFigDtVal.append(distV1lu)
                distFigDtPer.append(distP1lu)

                maxDist.append(max(distV1lu))
                minDist.append(min(distV1lu))

                # Slp
                slpV1lu = map(float, wslzjs[luidx]["Slope"]["Value"])
                slpP1lu = map(float, wslzjs[luidx]["Slope"]["Percent"])
                slpFigDtVal.append(slpV1lu)
                slpFigDtPer.append(slpP1lu)

                maxSlp.append(max(slpV1lu))
                minSlp.append(min(slpV1lu))

        max_elev = max(maxElev)
        max_dist = max(maxDist)
        max_slp = max(maxSlp)
        min_elev = min(minElev)
        min_dist = min(minDist)
        min_slp = min(minSlp)

        #subareaNo, sublz, 
        #    fig_elev, fig, figureidx, ttsubnos, cols
        # plotting elevation
        self.plotting(lulist, 
                elevFigDtVal, elevFigDtPer, 
                "Elevation(m)", "Accumulated percent of\n area (%)",
                min_elev, max_elev, fig_elev)

        self.plotting(lulist, 
                distFigDtVal,distFigDtPer, 
                "Distance(m)", "Accumulated percent of\n area (%)",
                min_dist, max_dist, fig_dist)

        self.plotting(lulist, 
                slpFigDtVal,slpFigDtPer, 
                "Slope(degree)", "Accumulated percent of\n area (%)",
                min_slp, max_slp, fig_slp)

    def plotting(self, 
            lulist,
            valuelist,
            perlist,
            xlabeltext,
            ylabeltext,
            min_value, max_value,
            fnoutfig
            ):

        # Start plotting
        fig = None
        fig = plt.figure(figsize=(9,7), dpi=200)

        # xlabelfontsize = 20
        # ylabelfontsize = 20
        # tickfontsize = 20
        # legendfontsize = 18
        # legend_properties = {'weight':'light'}
        # xytickfontproperties = {'family':'sans-serif',
        #                         'sans-serif':['Helvetica'],
        #                         'weight' : 'light',
        #                         'size' : tickfontsize}

        ax = fig.add_subplot(111)

        # Plot for all lines
        # Plot srclu: 
        for lidx in range(len(lulist)-1):
            ax.plot(valuelist[lidx], perlist[lidx], linewidth=2.0, label=str(lulist[lidx]))
        
        # Control legend
        legd = ax.legend(loc="center left", 
               bbox_to_anchor=[1, 0.5],
               ncol=1, 
               shadow=False, 
               title="Land use",
               fontsize = 9) 
        art = []
        art.append(legd)
        
        box = ax.get_position()
        # setposition(left, bottom, width, height)
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    
        # Control label
        # set: a property batch setter
        # set_xlabel(xlabel, labelpad, **kwargs)
        ax.set_xlabel(xlabeltext, fontsize=14)
        ax.set_ylabel(ylabeltext, fontsize=14)

        # Control grids
        ax.grid()
                
        # Control ticks
        ax.set_xlim(left=min_value, 
                  right=max_value)

        ax.set_ylim(bottom=0, 
                    top=100)
        
        ax.tick_params(labelsize=25)

        fig.savefig(fnoutfig, additional_artists=art,bbox_inches="tight")
        del(fig)
        del(fnoutfig)


class taudemfuncs(object):
    """
    The structure of this tool is following that in the TauDEMUtil.py
    available in QSWATplus package developed by Chris George, with necessay
    modification to be able to work with ArcPY
    """

    def __init__(self):

        # Subprocess calls with full path does not give error.
        self.maindir = os.path.dirname("D:\\gitrepos\\arcpysslmfp\\InstallationSource\\")
        self.TauDEMDir = os.path.join(self.maindir, "TauDEM_Exe_64")
        self.mpiexecPath = r"C:\\Program Files\\Microsoft MPI\\Bin\\mpiexec.exe"


    def runPitRemove(self, demFile, felFile, numProcesses):
        """Run PitFill."""
        return self.run('pitremove',
                               [('-z', demFile)],
                               [],
                               [('-fel', felFile)], 
                               numProcesses)

    def runD8FlowDir(self, felFile, sd8File, pFile, numProcesses):
        """Run D8FlowDir."""
        return self.run('d8flowdir',
                               [('-fel', felFile)],
                               [],
                               [('-sd8', sd8File),
                                ('-p', pFile)], 
                                numProcesses)

    def runAreaD8(self, pFile, ad8File, outletFile, 
            weightFile, numProcesses, contCheck):
        """Run AreaD8."""
        inFiles = [('-p', pFile)]
        if outletFile is not None:
            inFiles.append(('-o', outletFile))
        if weightFile is not None:
            inFiles.append(('-wg', weightFile))
        check = [] if contCheck == "false" else [('-nc', '')]
        return self.run('aread8', inFiles, check, [('-ad8', ad8File) ], numProcesses)

    def runThreshold(self, ad8File, srcFile, threshold, numProcesses):
        """Run Threshold."""
        return self.run('threshold', 
            [('-ssa', ad8File)],
            [('-thresh', threshold)],
            [('-src', srcFile)], numProcesses)
    

    def runMoveOutlets(self, pFile, srcFile, outletFile, movedOutletFile, numProcesses, maxDist):
        """Run MoveOutlets."""
        return self.run('moveoutletstostreams',
                [('-p', pFile), ('-src', srcFile),
                 ('-o', outletFile)], 
                [('-md', maxDist)],
                [('-om', movedOutletFile)], 
                               numProcesses)

    def runStreamNet(self, felFile, pFile, ad8File, srcFile, outletFile, ordFile, 
            treeFile, coordFile, streamFile, wFile, single, numProcesses):
        """Run StreamNet."""
        inFiles = [('-fel', felFile), ('-p', pFile), ('-ad8', ad8File), ('-src', srcFile)]
        if outletFile is not None:
            inFiles.append(('-o', outletFile))
        inParms = [('-sw', '')] if single else []
        return self.run('streamnet', inFiles, inParms, 
                               [('-ord', ordFile), ('-tree', treeFile), ('-coord', coordFile), ('-net', streamFile), ('-w', wFile)], 
                               numProcesses)

    def runDist2SubOlt(self, pfile, wfile, srcfile, d2soltfile, numProcesses):
        """Run dist2subolt.
        mpiexec -n <number of processes> dist2subolt -p <pfile> -ws <wfile> -src <srcfile> -dist <d2soltfile>   
        """
        return self.run('dist2subolt',
                               [('-p', pfile),
                                ('-ws', wfile),
                                ('-src', srcfile)],
                               [],
                               [('-dist', d2soltfile)], 
                                numProcesses)

    def runDist2WsOlt(self, pfile, srcfile, d2woltfile, numProcesses):
        """Run dist2wsolt.
        mpiexec -n <number of processes> dist2wsolt -p <pfile> -src <srcfile> -dist <d2woltfile>   
        """
        return self.run('dist2wsolt',
                               [('-p', pfile),
                                ('-src', srcfile)],
                               [],
                               [('-dist', d2woltfile)], 
                                numProcesses)

    def runlurenzfpsub(self, pfile, d2soltfile, wfile, inLu, inElev, inSlp, outLzJS, numProcesses):
        """Run lorenzfpsub.
        mpiexec -n <number of processes> lorenzfpsub -p <pfile> -d2so <d2soltfile> -ws <wfile> -lu <inLu>
        -elev <inElev> -slp <inSlp> -lzjss <outLzJS>   
        """
        return self.run('lorenzfpsub.exe',
                               [('-p', pfile),
                                ('-d2so', d2soltfile),
                                ('-ws', wfile),
                                ('-lu', inLu),
                                ('-elev', inElev),
                                ('-slp', inSlp)],
                               [],
                               [('-lzjss', outLzJS)], 
                                numProcesses)

    def runlorenzfpws(self, pfile, d2woltfile, wfile, inLu, inElev, inSlp, outLzJSW, numProcesses):
        """Run lorenzfpws.
        mpiexec -n <number of processes> lorenzfpws -p <pfile> -d2wo <d2soltfile> -ws <wfile> -lu <inLu>
        -elev <inElev> -slp <inSlp> -lzjsw <outLzJSW>   
        """
        return self.run('lorenzfpws.exe',
                               [('-p', pfile),
                                ('-d2wo', d2woltfile),
                                ('-ws', wfile),
                                ('-lu', inLu),
                                ('-elev', inElev),
                                ('-slp', inSlp)],
                               [],
                               [('-lzjsw', outLzJSW)], 
                                numProcesses)


    def runsubindexmap(self, wfile, inSubJson, outSslmSub, numProcesses):
        """Run Dist2SubOlt.
        mpiexec -n <number of processes> subindexmap -ws <wfile>
        -ijs inSubJson -ims outSslmSub   
        """
        return self.run('subindexmap',
                               [('-ws', wfile),
                                ('-ijs', inSubJson)],
                               [],
                               [('-ims', outSslmSub)], 
                                numProcesses)






    def run(self, command, 
            inFiles, 
            inParms, 
            outFiles, 
            numProcesses):
        """Run PitFill."""

        commands = []

        if numProcesses != "0":
            mpiexecPath = self.mpiexecPath
            if mpiexecPath != '':
                commands.append(mpiexecPath)
                commands.append('-np') # -n acceptable in Windows but only -np in OpenMPI
                commands.append(str(numProcesses))

        arcpy.AddMessage(self.TauDEMDir)

        if self.TauDEMDir == '':
            arcpy.AddMessage("\nTauDEM Folder is not correct, please check")
            return False
        else:
            taudemCmd = os.path.join(self.TauDEMDir, command)
            commands.append(taudemCmd)

        for (pid, fileName) in inFiles:
            commands.append(pid)
            commands.append(fileName)

        for (pid, parm) in inParms:
            commands.append(pid)
            # allow for parameter which is flag with no value
            if not parm == '':
                commands.append(parm)
        for (pid, fileName) in outFiles:

            # Delete outfile if exists
            if arcpy.Exists(fileName):
                arcpy.Delete_management(fileName)

            commands.append(pid)
            commands.append(fileName)

        command = ' '.join(commands) 

        arcpy.AddMessage(command)
        procs = self.execute_command(command)
        #arcpy.AddMessage(procs)


    def execute_command(self, command):
        # hide console window on windows
        # if os.name == 'nt':
        #     startupinfo = subprocess.STARTUPINFO()
        #     startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        output = None
        try:
            output = subprocess.check_output(
                command,
                shell=True
            )
        except (subprocess.CalledProcessError, AttributeError):
            # Git will return an error when the given directory
            # is not a repository, which means that we can ignore this error
            pass
        else:
            output = str(output).strip()

        return output 