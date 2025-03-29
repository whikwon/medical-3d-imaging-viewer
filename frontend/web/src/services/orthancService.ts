import type { Patient, Series, Study } from '@/types/orthanc'

/**
 * Fetches a list of all patients from the Orthanc server
 */
export async function fetchPatients(): Promise<Patient[]> {
  const response = await fetch('/api/orthanc/patients')
  if (!response.ok) {
    throw new Error(`Failed to fetch patients: ${response.statusText}`)
  }
  return response.json()
}

/**
 * Fetches a list of all studies from the Orthanc server
 */
export async function fetchStudies(): Promise<Study[]> {
  const response = await fetch('/api/orthanc/studies')
  if (!response.ok) {
    throw new Error(`Failed to fetch studies: ${response.statusText}`)
  }
  return response.json()
}

/**
 * Fetches all series for a specific study from the Orthanc server
 * @param studyId - The ID of the study to fetch series for
 */
export async function fetchSeriesForStudy(studyId: string): Promise<Series[]> {
  const response = await fetch(`/api/orthanc/studies/${studyId}/series`)
  if (!response.ok) {
    throw new Error(`Failed to fetch series: ${response.statusText}`)
  }
  return response.json()
}

/**
 * Fetches series data from the Orthanc server
 * @param seriesId - The ID of the series to fetch data for
 */
export async function fetchSeriesData(seriesId: string): Promise<{
  data: Blob
  windowWidth: number
  windowCenter: number
}> {
  const response = await fetch(`/api/orthanc/series/${seriesId}/data`)
  if (!response.ok) {
    throw new Error(`Failed to fetch series data: ${response.statusText}`)
  }

  const windowWidth = Number(response.headers.get('X-Window-Width') || '400')
  const windowCenter = Number(response.headers.get('X-Window-Center') || '40')

  return {
    data: await response.blob(),
    windowWidth,
    windowCenter,
  }
}

/**
 * Fetches the list of available label filenames for a specific series
 * @param seriesId - The Orthanc ID of the series
 */
export async function fetchAvailableLabels(seriesId: string): Promise<string[]> {
  // Use the endpoint you created on the backend.
  // Assuming it directly returns the list based on Orthanc series ID.
  const response = await fetch(`/api/orthanc/series/${seriesId}/label_list`)
  if (!response.ok) {
    throw new Error(`Failed to fetch available labels: ${response.statusText}`)
  }
  const labelPaths: string[] = await response.json()
  // The backend returns full paths, let's extract just the filenames
  return labelPaths.map((path) => path.substring(path.lastIndexOf('/') + 1))
}

/**
 * Fetches the content of a specific label file for a series
 * @param seriesId - The Orthanc ID of the series
 * @param labelFilename - The filename of the label to fetch
 */
export async function fetchLabelContent(seriesId: string, labelFilename: string): Promise<any> {
  // Assuming the backend endpoint structure is /api/series/{seriesId}/labels/{filename}
  const response = await fetch(
    `/api/orthanc/series/${seriesId}/labels/${encodeURIComponent(labelFilename)}`,
  )
  if (!response.ok) {
    throw new Error(`Failed to fetch label content for ${labelFilename}: ${response.statusText}`)
  }
  // Assuming the label content is JSON
  return response.json()
}
