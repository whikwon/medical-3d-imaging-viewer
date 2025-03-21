/**
 * Study interface represents a study in the Orthanc server
 */
export interface DicomTags {
  PatientName?: string
  StudyDescription?: string
  SeriesDescription?: string
  SeriesNumber?: string
  Modality?: string
  [key: string]: string | undefined
}

export interface Study {
  ID: string
  IsStable: boolean
  LastUpdate: string
  MainDicomTags: DicomTags
  ParentPatient: string
  PatientMainDicomTags: DicomTags
  Series: string[]
  Type: string
}

/**
 * Series interface represents a series within a study in the Orthanc server
 */
export interface Series {
  ID: string
  Instances: string[]
  IsStable: boolean
  LastUpdate: string
  MainDicomTags: DicomTags
  ParentStudy: string
  Status: string
  Type: string
}
