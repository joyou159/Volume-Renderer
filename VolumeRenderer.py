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
        self.volume = None
        self.iso_value = 0
        self.intensity_values = list()
        self.visualize_flag = 0  # means nothing is visualized
        self.main_window.ui.IsoValueSlider.valueChanged.connect(
            self.handle_iso_value)
        self.renderer = vtk.vtkRenderer()
        self.render_window = vtk_widget.GetRenderWindow()
        self.render_window.AddRenderer(self.renderer)
        headlight = vtk.vtkLight()
        headlight.SetLightTypeToHeadlight()
        self.renderer.AddLight(headlight)

        # Set up the camera
        self.camera = self.renderer.GetActiveCamera()
        self.camera.SetPosition(0, 0, 300)
        self.camera.SetFocalPoint(0, 0, 0)

        # Additional initialization if needed
    def compute_intensity_values(self):
        scalar_range = self.volume.GetOutput().GetScalarRange()
        self.intensity_values = list(
            range(int(scalar_range[0]), int(scalar_range[1]) + 1))
        self.set_iso_sliders()

    def apply_gaussian_smoothing(self, volume):
        gaussian_smooth = vtk.vtkImageGaussianSmooth()
        gaussian_smooth.SetInputData(volume)  # Set the input directly
        gaussian_smooth.SetStandardDeviation(1.0)
        gaussian_smooth.Update()
        return gaussian_smooth.GetOutput()

    def create_volume_actor(self, mapper, volume_property):
        volume_actor = vtk.vtkVolume()
        volume_actor.SetMapper(mapper)
        volume_actor.SetProperty(volume_property)
        return volume_actor

    def add_reference_axes(self):
        # Create a vtkCubeAxesActor2D
        cube_axes = vtk.vtkCubeAxesActor2D()

        # Get bounds from the vtkRenderWindow
        bounds = self.render_window.GetRenderers(
        ).GetFirstRenderer().ComputeVisiblePropBounds()
        cube_axes.SetBounds(bounds)

        cube_axes.SetCamera(self.renderer.GetActiveCamera())
        cube_axes.SetLabelFormat("%6.4g")
        cube_axes.SetFlyModeToOuterEdges()

        # Create a vtkTextProperty for the cube axes labels
        text_property = vtk.vtkTextProperty()
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

        color_transfer_function = vtk.vtkColorTransferFunction()
        color_transfer_function.AddRGBPoint(0, 0.0, 0.0, 0.0)
        color_transfer_function.AddRGBPoint(200, 1.0, 1.0, 1.0)
        volume_property.SetColor(color_transfer_function)

        opacity_transfer_function = vtk.vtkPiecewiseFunction()
        opacity_transfer_function.AddPoint(0, 0.0)
        opacity_transfer_function.AddPoint(80, 0.1)
        opacity_transfer_function.AddPoint(120, 0.8)
        opacity_transfer_function.AddPoint(255, 1.0)
        volume_property.SetScalarOpacity(opacity_transfer_function)

        smoothed_volume = self.apply_gaussian_smoothing(volume)

        ray_cast_mapper.SetInputData(smoothed_volume)

        volume_actor = self.create_volume_actor(
            ray_cast_mapper, volume_property)

        self.renderer.AddVolume(volume_actor)

        self.renderer.SetBackground(0, 0, 0)
        volume_property.ShadeOn()
        ray_cast_mapper.SetUseJittering(True)
        ray_cast_mapper.SetSampleDistance(0.1)

        self.renderer.ResetCamera()
        self.add_reference_axes()

    def update_visualization(self):
        if self.volume:
            current_position = self.camera.GetPosition()
            current_focal_point = self.camera.GetFocalPoint()
            current_zoom = self.camera.GetDistance()
            self.renderer.RemoveAllViewProps()
            # Check the rendering mode and update the visualization accordingly
            if self.main_window.rendering_mode == 0:
                # Surface Rendering
                self.surface_rendering(self.volume.GetOutput(), self.iso_value)
            elif self.main_window.rendering_mode == 1:
                # Ray Casting Rendering
                self.ray_casting_rendering(self.volume.GetOutput())
            self.camera.SetPosition(current_position)
            self.camera.SetFocalPoint(current_focal_point)
            self.camera.SetDistance(current_zoom)
            self.render_window.Render()
            self.visualize_flag = 1

    def handle_iso_value(self):
        self.iso_value = self.main_window.ui.IsoValueSlider.value()
        self.main_window.ui.IsoValue.setText(f"Iso Value: {self.iso_value}")
        self.update_visualization()

    def set_iso_sliders(self):
        self.main_window.ui.IsoValueSlider.setMaximum(
            self.intensity_values[-1])
        self.main_window.ui.IsoValueSlider.setMinimum(
            self.intensity_values[0])
        self.main_window.ui.IsoValueSlider.setValue(
            self.intensity_values[len(self.intensity_values)//2])

    def surface_rendering(self, volume, iso_value):
        smoothed_volume = self.apply_gaussian_smoothing(volume)

        contour_filter = vtk.vtkContourFilter()
        contour_filter.SetInputData(smoothed_volume)
        contour_filter.GenerateValues(1, iso_value, iso_value)

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
