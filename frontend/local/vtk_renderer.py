import numpy as np
import vtk


class VtkRenderer:
    def __init__(self, window_size=(600, 600), background_color=(1.0, 1.0, 1.0)):
        self.window_size = window_size
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(*background_color)

        self.render_window = vtk.vtkRenderWindow()
        self.render_window.AddRenderer(self.renderer)
        self.render_window.SetSize(*self.window_size)
        self.render_window.SetFullScreen(True)

        self.interactor = vtk.vtkRenderWindowInteractor()
        self.interactor.SetRenderWindow(self.render_window)
        self.interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

    def add_image(self, image_data):
        """Add a VTK image to the renderer"""
        image_actor = vtk.vtkImageActor()
        image_actor.GetMapper().SetInputData(image_data)
        self.renderer.AddActor(image_actor)
        return image_actor

    def add_axes(self, length=40, cylinder_radius=0.02):
        """Add coordinate axes to the renderer"""
        axes = vtk.vtkAxesActor()
        axes.SetXAxisLabelText("X")
        axes.SetYAxisLabelText("Y")
        axes.SetZAxisLabelText("Z")
        axes.SetTotalLength(length, length, length)
        axes.SetShaftTypeToCylinder()
        axes.SetCylinderRadius(cylinder_radius)
        self.renderer.AddActor(axes)
        return axes

    def add_centerline(self, points, tube_radius=0.5, color=(1.0, 0.0, 0.0)):
        """
        Add a centerline visualization as a tube filter to the renderer

        Args:
            points: Numpy array of shape (n, 3) containing the centerline points
            tube_radius: Radius of the tube filter
            color: RGB color tuple (values between 0 and 1)

        Returns:
            The tube actor that was added to the renderer
        """
        # Create a vtkPoints object and add the points
        vtk_points = vtk.vtkPoints()
        for point in points:
            vtk_points.InsertNextPoint(point[0], point[1], point[2])

        # Create a polyline from the points
        polyline = vtk.vtkPolyLine()
        polyline.GetPointIds().SetNumberOfIds(len(points))
        for i in range(len(points)):
            polyline.GetPointIds().SetId(i, i)

        # Create a cell array to store the polyline
        cells = vtk.vtkCellArray()
        cells.InsertNextCell(polyline)

        # Create a polydata to store the points and lines
        polydata = vtk.vtkPolyData()
        polydata.SetPoints(vtk_points)
        polydata.SetLines(cells)

        # Create a tube filter and set the polydata as input
        tube_filter = vtk.vtkTubeFilter()
        tube_filter.SetInputData(polydata)
        tube_filter.SetRadius(tube_radius)
        tube_filter.SetNumberOfSides(16)
        tube_filter.CappingOn()
        tube_filter.Update()

        # Create a mapper and actor for the tube
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(tube_filter.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(color)

        # Add the actor to the renderer
        self.renderer.AddActor(actor)

        return actor

    def set_camera(self, position, focal_point, view_up):
        """Set the camera to the renderer"""
        camera = vtk.vtkCamera()
        camera.SetPosition(position)
        camera.SetFocalPoint(focal_point)
        camera.SetViewUp(view_up)
        self.renderer.SetActiveCamera(camera)

    def reset_camera(self):
        """Reset the camera to view all objects"""
        self.renderer.ResetCamera()

    def render(self):
        """Render the scene"""
        self.render_window.Render()

    def start_interaction(self):
        """Start interactive visualization"""
        self.render()
        self.interactor.Start()
