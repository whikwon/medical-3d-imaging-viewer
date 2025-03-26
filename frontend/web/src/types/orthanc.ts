/**
 * Study interface represents a study in the Orthanc server
 */
export interface DicomTags {
  PatientName?: string
  StudyDescription?: string
  SeriesDescription?: string
  SeriesNumber?: string
  Modality?: string
  PatientID?: string
  [key: string]: string | undefined
}

export interface Patient {
  ID: string
  IsStable: boolean
  LastUpdate: string
  MainDicomTags: DicomTags
  PatientMainDicomTags: DicomTags
  Studies: string[]
  StudiesCount: number
  Type: string
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
