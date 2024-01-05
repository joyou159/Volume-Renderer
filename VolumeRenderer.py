import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QFileDialog, QWidget, QMessageBox
from PyQt5.QtCore import QTimer
from PyQt5.uic import loadUi
import vtk
import os
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import numpy as np


class VolumeRenderer:
    def __init__(self, vtk_widget, main_window):
        self.vtk_widget = vtk_widget
        self.main_window = main_window
        self.volume = None  # the VTK DICOM image reader
        self.iso_value = 0
        # all the intensity values to be used in visualization
        self.intensity_values = list()
        # means nothing is visualized (used for reimporting)
        self.visualize_flag = 0

        self.main_window.ui.IsoValueSlider.valueChanged.connect(
            self.handle_iso_value)

        self.renderer = vtk.vtkRenderer()
        self.render_window = vtk_widget.GetRenderWindow()
        self.render_window.AddRenderer(self.renderer)

        # head light setup
        headlight = vtk.vtkLight()
        headlight.SetLightTypeToHeadlight()
        self.renderer.AddLight(headlight)

        # Set up the camera
        self.camera = self.renderer.GetActiveCamera()
        self.camera.SetPosition(0, 0, 300)
        self.camera.SetFocalPoint(0, 0, 0)

    def compute_intensity_values(self):
        """
        Compute intensity values from the scalar range of the loaded volume.

        This function retrieves the scalar range from the loaded volume using VTK.
        It then generates a list of integer intensity values covering the entire
        scalar range, inclusive. The computed intensity values can be used, for example,
        in setting up sliders for iso-surface extraction thresholds.

       """
        smoothed_volume = self.apply_gaussian_smoothing(
            self.volume.GetOutput())
        scalar_range = smoothed_volume.GetScalarRange()
        self.intensity_values = list(
            range(int(scalar_range[0]), int(scalar_range[1]) + 1))
        self.set_iso_sliders()

    def apply_gaussian_smoothing(self, volume):
        """
            Apply Gaussian smoothing to a 3D volume using VTK.

            This function takes a VTK volume as input, applies Gaussian smoothing using
            vtkImageGaussianSmooth, and returns the smoothed volume.
        """
        gaussian_smooth = vtk.vtkImageGaussianSmooth()
        gaussian_smooth.SetInputData(volume)
        gaussian_smooth.SetStandardDeviation(1.0)
        gaussian_smooth.Update()
        return gaussian_smooth.GetOutput()

    def create_volume_actor(self, mapper, volume_property):
        """   
            Create a VTK volume actor with the specified mapper and property.

            This function creates a VTK volume actor using the provided mapper and
            volume property. The resulting actor can be added to a VTK renderer for
            visualization.
        """
        volume_actor = vtk.vtkVolume()
        volume_actor.SetMapper(mapper)
        volume_actor.SetProperty(volume_property)
        return volume_actor

    def add_reference_axes(self):
        """
            Add reference axes (cube axes) to the current VTK renderer.

            This function adds a cube axes actor to the VTK renderer. The cube axes provide
            reference axes aligned with the coordinate system of the rendered scene. It helps
            in understanding the orientation and scale of the rendered volume.
        """
        cube_axes = vtk.vtkCubeAxesActor2D()  # actor

        # Get bounds from the vtkRenderWindow
        bounds = self.render_window.GetRenderers(
        ).GetFirstRenderer().ComputeVisiblePropBounds()
        cube_axes.SetBounds(bounds)

        cube_axes.SetCamera(self.renderer.GetActiveCamera())
        cube_axes.SetLabelFormat("%6.4g")  # g --> most compact representation
        cube_axes.SetFlyModeToOuterEdges()

        # Create a vtkTextProperty for the cube axes labels
        text_property = vtk.vtkTextProperty()  # actor
        text_property.BoldOn()
        text_property.ItalicOn()
        text_property.ShadowOn()
        text_property.SetFontSize(12)

        # Set the text property for the axes labels
        cube_axes.GetAxisLabelTextProperty().ShallowCopy(text_property)

        # Set the line width for the entire axis text
        cube_axes.GetAxisLabelTextProperty().SetFrameWidth(2)
        cube_axes.GetAxisLabelTextProperty().SetFrameWidth(2)
        cube_axes.GetAxisLabelTextProperty().SetFrameWidth(2)

        # Add the cube axes to the renderer
        self.renderer.AddViewProp(cube_axes)

    def ray_casting_rendering(self, volume):

        ray_cast_mapper = vtk.vtkGPUVolumeRayCastMapper()
        ray_cast_mapper.SetInputData(volume)
        ray_cast_mapper.SetBlendModeToComposite()

        volume_property = vtk.vtkVolumeProperty()
        volume_property.SetIndependentComponents(1)
        volume_property.ShadeOn()

        # Create a color transfer function
        color_transfer_function = vtk.vtkColorTransferFunction()

        # Add control points to the color transfer function
        color_transfer_function.AddRGBPoint(0, 0.0, 0.0, 0.0)
        color_transfer_function.AddRGBPoint(200, 1.0, 1.0, 1.0)

        # Set the color transfer function in the volume property
        volume_property.SetColor(color_transfer_function)

        # Create an opacity transfer function
        opacity_transfer_function = vtk.vtkPiecewiseFunction()

        # Add control points to the opacity transfer function
        opacity_transfer_function.AddPoint(0, 0.0)
        opacity_transfer_function.AddPoint(80, 0.1)
        opacity_transfer_function.AddPoint(120, 0.8)
        opacity_transfer_function.AddPoint(255, 1.0)

        # Set the opacity transfer function in the volume property
        volume_property.SetScalarOpacity(opacity_transfer_function)

        # apply filter
        smoothed_volume = self.apply_gaussian_smoothing(volume)

        ray_cast_mapper.SetInputData(smoothed_volume)  # reset input data

        volume_actor = self.create_volume_actor(
            ray_cast_mapper, volume_property)

        self.renderer.AddVolume(volume_actor)

        self.renderer.SetBackground(0, 0, 0)
        volume_property.ShadeOn()
        # Jittering is a technique often used in computer graphics to reduce aliasing artifacts
        ray_cast_mapper.SetUseJittering(True)
        ray_cast_mapper.SetSampleDistance(0.001)

        self.renderer.ResetCamera()
        self.add_reference_axes()

    def update_visualization(self):
        if self.volume:
            # retain the current camera position, focal point and zooming to rerendering
            current_position = self.camera.GetPosition()
            current_focal_point = self.camera.GetFocalPoint()
            current_zoom = self.camera.GetDistance()

            # remove the previous actors to prevent accumulation of actors
            self.renderer.RemoveAllViewProps()

            # Check the rendering mode and update the visualization accordingly
            if self.main_window.rendering_mode == 0:
                # Surface Rendering
                self.surface_rendering(self.volume.GetOutput(), self.iso_value)
            elif self.main_window.rendering_mode == 1:
                # Ray Casting Rendering
                self.ray_casting_rendering(self.volume.GetOutput())

            # reset the camera position, focal point and zooming
            self.camera.SetPosition(current_position)
            self.camera.SetFocalPoint(current_focal_point)
            self.camera.SetDistance(current_zoom)

            self.render_window.Render()

    def handle_iso_value(self):
        self.iso_value = self.main_window.ui.IsoValueSlider.value()
        self.main_window.ui.IsoValue.setText(f"Iso Value: {self.iso_value}")
        self.update_visualization()

    def set_iso_sliders(self):
        """ initializing the slider values and set the current value to the middle of the slider.
        """
        self.main_window.ui.IsoValueSlider.setMaximum(
            self.intensity_values[-1])
        self.main_window.ui.IsoValueSlider.setMinimum(
            self.intensity_values[0])
        self.main_window.ui.IsoValueSlider.setValue(
            self.intensity_values[len(self.intensity_values)//2])

    def calculate_contour_number(self, iso_value):
        # Determine the number of contours based on the iso-value and intensity range
        num_contours = len(
            [value for value in self.intensity_values if value <= iso_value])
        return num_contours

    def surface_rendering(self, volume, iso_value):
        # apply gaussian filter, helps to reduce noise and artifacts in the data,
        # leading to a smoother and more visually appealing surface when rendering.
        smoothed_volume = self.apply_gaussian_smoothing(volume)

        # Contour extraction is a technique where surfaces are defined based on specific scalar values (iso-value) in the volume data
        contour_filter = vtk.vtkContourFilter()
        contour_filter.SetInputData(smoothed_volume)
        # (number of contours, maximum contour value , minimum contour value)

        # can't control the number of contours as it case a crash
        contour_filter.GenerateValues(
            5, iso_value, self.intensity_values[0])
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(contour_filter.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.SetPosition(0, 0, 0)

        self.renderer.AddActor(actor)

        self.renderer.SetBackground(0, 0, 0)
        self.renderer.ResetCamera()
        self.add_reference_axes()
        self.visualize_flag = 1
