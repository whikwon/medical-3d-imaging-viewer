# Medical 3D Imaging Viewer - VTK Visualization Module

This directory contains a modular implementation of a VTK-based medical imaging viewer.

## Module Structure

The code has been separated into the following modules for better maintainability:

1. **dicom_loader.py**: Handles loading and parsing DICOM data from Orthanc

   - `DicomLoader` class: Loads studies and series from Orthanc and creates CArm objects

2. **vtk_image_creator.py**: Converts DICOM data to VTK image format

   - `VtkImageCreator` class: Creates VTK image data with proper orientation and spacing

3. **vtk_renderer.py**: Manages the visualization and rendering of VTK images

   - `VtkRenderer` class: Sets up the rendering pipeline, handles actors and interactions

4. **main.py**: Main entry point for the application

   - Uses the other modules to create a complete visualization pipeline

5. **vtk_test.py**: Legacy wrapper script that uses the modular implementation
   - Maintained for backward compatibility

## Usage

To run the visualization:

```bash
python main.py
```

## Dependencies

- VTK
- NumPy
- pyorthanc
- Backend app modules (app.core.carm, app.core.dicom)
