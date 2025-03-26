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
