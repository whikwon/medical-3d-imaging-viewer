import type { Series, Study } from '@/types/orthanc'

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
 * Fetches the VTI data for a specific series from the Orthanc server
 * @param seriesId - The ID of the series to fetch data for
 */
export async function fetchSeriesData(seriesId: string): Promise<Blob> {
  const response = await fetch(`/api/orthanc/series/${seriesId}/data`)
  if (!response.ok) {
    throw new Error(`Failed to fetch series data: ${response.statusText}`)
  }
  return response.blob()
}
