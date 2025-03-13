/**
 * Helper functions for interacting with the Orthanc API via FastAPI
 */

// Get the API server URL from environment variables
const API_URL = import.meta.env.VITE_API_URL 

// Function to get the appropriate URL (with proxy in development, direct in production)
function getApiUrl(path: string): string {
  return `${API_URL}/api/v1/orthanc${path}`;
}

// Common fetch options
const fetchOptions: RequestInit = {
  headers: {
    'Content-Type': 'application/json'
  }
};

/**
 * Get a list of all studies in the Orthanc server
 */
export async function getStudies() {
  const response = await fetch(getApiUrl('/studies'), fetchOptions);
  
  if (!response.ok) {
    throw new Error(`Failed to retrieve studies: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get detailed information about a specific study
 */
export async function getStudy(studyId: string) {
  const response = await fetch(getApiUrl(`/studies/${studyId}`), fetchOptions);
  
  if (!response.ok) {
    throw new Error(`Failed to retrieve study: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get a list of all series in a study
 */
export async function getSeriesForStudy(studyId: string) {
  const response = await fetch(getApiUrl(`/studies/${studyId}/series`), fetchOptions);
  
  if (!response.ok) {
    throw new Error(`Failed to retrieve series: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get a list of all instances in a series
 */
export async function getInstancesForSeries(seriesId: string) {
  const response = await fetch(getApiUrl(`/series/${seriesId}/instances`), fetchOptions);
  
  if (!response.ok) {
    throw new Error(`Failed to retrieve instances: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get detailed information about a specific instance
 */
export async function getInstance(instanceId: string) {
  const response = await fetch(getApiUrl(`/instances/${instanceId}`), fetchOptions);
  
  if (!response.ok) {
    throw new Error(`Failed to retrieve instance: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Generate a Cornerstone-compatible image ID for a DICOM instance in Orthanc
 */
export function getOrthancImageId(instanceId: string) {
  // For Cornerstone, we need to format this as a wado URI
  // The format is: 'wadouri:' + URL to the DICOM file
  const instanceUrl = getApiUrl(`/instances/${instanceId}/file`);
  
  // For Cornerstone's DICOM image loader, we need to handle auth differently
  // This will depend on how you've configured the loader
  return `wadouri:${instanceUrl}`;
}

/**
 * Get a list of available instances and generate Cornerstone image IDs for them
 */
export async function getAvailableImageIds() {
  // Get all studies
  const studyIdList = await getStudies();

  // For now, just use the first study
  if (studyIdList.length === 0) {
    throw new Error('No studies found in Orthanc server');
  }
  
  const studyId = studyIdList[1];
  
  // Get all series in the study
  const seriesList = await getSeriesForStudy(studyId);
  
  if (seriesList.length === 0) {
    throw new Error('No series found in study');
  }
  
  // For now, just use the first series
  const series = seriesList[0];
  
  // Get all instances in the series
  const instances = await getInstancesForSeries(series.ID);
  
  if (instances.length === 0) {
    throw new Error('No instances found in series');
  }
  
  // Fetch detailed information for each instance
  const instancePromises = instances.map((instance: any) => getInstance(instance.ID));
  const instanceDetails = await Promise.all(instancePromises);
  
  // Sort instances by appropriate criteria
  // First try to sort by ImagePositionPatient, fallback to InstanceNumber
  const sortedInstances = sortInstances(instanceDetails);
  
  // Generate image IDs for sorted instances
  return sortedInstances.map((instance: any) => getOrthancImageId(instance.ID));
}

/**
 * Sort instances based on appropriate DICOM attributes
 * First tries ImagePositionPatient, then falls back to InstanceNumber
 */
function sortInstances(instances: any[]): any[] {
  // Check if all instances have valid ImagePositionPatient and ImageOrientationPatient
  const allHavePositionAndOrientation = instances.every(instance => 
    instance.MainDicomTags.ImagePositionPatient && 
    instance.MainDicomTags.ImageOrientationPatient
  );
  
  if (allHavePositionAndOrientation) {
    // Sort by position along the normal vector of the acquisition plane
    return sortByImagePosition(instances);
  } else {
    // Fallback to InstanceNumber
    return sortByInstanceNumber(instances);
  }
}

/**
 * Sort instances by ImagePositionPatient along the acquisition plane normal
 */
function sortByImagePosition(instances: any[]): any[] {
  // Get the orientation from the first instance (assuming all have same orientation)
  const firstInstance = instances[0];
  const orientation = firstInstance.MainDicomTags.ImageOrientationPatient
    .split('\\')
    .map(Number);
  
  // Calculate the normal vector to the acquisition plane
  const rowX = orientation[0], rowY = orientation[1], rowZ = orientation[2];
  const colX = orientation[3], colY = orientation[4], colZ = orientation[5];
  
  // Cross product to get the normal vector
  const normalX = rowY * colZ - rowZ * colY;
  const normalY = rowZ * colX - rowX * colZ;
  const normalZ = rowX * colY - rowY * colX;
  
  // Sort instances by their position along the normal vector
  return [...instances].sort((a, b) => {
    const posA = a.MainDicomTags.ImagePositionPatient.split('\\').map(Number);
    const posB = b.MainDicomTags.ImagePositionPatient.split('\\').map(Number);
    
    // Calculate dot product with normal vector
    const dotA = posA[0] * normalX + posA[1] * normalY + posA[2] * normalZ;
    const dotB = posB[0] * normalX + posB[1] * normalY + posB[2] * normalZ;
    
    return dotA - dotB;
  });
}

/**
 * Sort instances by InstanceNumber
 */
function sortByInstanceNumber(instances: any[]): any[] {
  return [...instances].sort((a, b) => {
    const instanceNumberA = parseInt(a.MainDicomTags.InstanceNumber || "0");
    const instanceNumberB = parseInt(b.MainDicomTags.InstanceNumber || "0");
    
    // If InstanceNumber is the same or invalid, try IndexInSeries
    if (isNaN(instanceNumberA) || isNaN(instanceNumberB) || instanceNumberA === instanceNumberB) {
      return (a.IndexInSeries || 0) - (b.IndexInSeries || 0);
    }
    
    return instanceNumberA - instanceNumberB;
  });
}