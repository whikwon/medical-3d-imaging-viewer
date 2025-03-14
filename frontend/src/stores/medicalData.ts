import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { 
  getStudies, 
  getStudy, 
  getSeriesForStudy, 
  getInstancesForSeries, 
  getOrthancImageId,
  getInstance,
  sortInstances
} from '../helpers/orthancApi'

export interface Patient {
  id: string
  name: string
  patientId: string
  studies: Study[]
}

export interface Study {
  id: string
  description: string
  date: string
  series: Series[]
}

export interface Series {
  id: string
  description: string
  modality: string
  instanceCount: number
  imageIds: string[]
}

export const useMedicalDataStore = defineStore('medicalData', () => {
  // State
  const patients = ref<Patient[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentPatientId = ref<string | null>(null)
  const currentStudyId = ref<string | null>(null)
  const currentSeriesId = ref<string | null>(null)

  // Getters
  const currentPatient = computed(() => 
    patients.value.find(p => p.id === currentPatientId.value) || null
  )
  
  const currentStudy = computed(() => {
    const patient = currentPatient.value
    if (!patient) return null
    return patient.studies.find(s => s.id === currentStudyId.value) || null
  })
  
  const currentSeries = computed(() => {
    const study = currentStudy.value
    if (!study) return null
    return study.series.find(s => s.id === currentSeriesId.value) || null
  })

  const currentImageIds = computed(() => 
    currentSeries.value?.imageIds || []
  )

  // Actions
  async function loadAllData() {
    try {
      loading.value = true
      error.value = null
      
      console.log('Starting to load medical data...')
      
      // Get all studies from Orthanc
      const studyIds = await getStudies()
      console.log('Retrieved studies:', studyIds.length)
      
      if (studyIds.length === 0) {
        console.warn('No studies found on Orthanc server')
        return
      }
      
      // Group studies by patient
      const patientMap = new Map<string, Patient>()
      
      // Process each study
      for (const studyId of studyIds) {
        console.log('Processing study:', studyId)
        const studyData = await getStudy(studyId)

        // Extract patient info
        const patientName = studyData.PatientMainDicomTags.PatientName || 'Unknown'
        const patientId = studyData.PatientMainDicomTags.PatientID 
        console.log('Patient info:', { patientId, patientName })
        
        // Create or get patient
        if (!patientMap.has(patientId)) {
          patientMap.set(patientId, {
            id: patientId,
            name: patientName,
            patientId: patientId,
            studies: []
          })
        }
        
        const patient = patientMap.get(patientId)!
        
        // Create study object
        const study: Study = {
          id: studyId,
          description: studyData.MainDicomTags.StudyDescription || 'No description',
          date: studyData.MainDicomTags.StudyDate || 'Unknown date',
          series: []
        }
        
        // Get series for this study
        const seriesList = await getSeriesForStudy(studyId)
        console.log('Series in study:', seriesList.length)
        
        // Process each series
        for (const series_ of seriesList) {
          const modality = series_.MainDicomTags.Modality
          const instances = await getInstancesForSeries(series_.ID)
          console.log('Instances in series:', instances.length)
          
          // Get first instance to extract series info
          if (instances.length > 0) {
            const firstInstance = instances[0]
            
            // Fetch detailed information for each instance to enable proper sorting
            const instancePromises = instances.map((instance: any) => getInstance(instance.ID))
            const instanceDetails = await Promise.all(instancePromises)
            
            // Sort instances using the same logic as in orthancApi.ts
            const sortedInstances = sortInstances(instanceDetails)
            
            // Create series object
            const series: Series = {
              id: series_.ID,
              description: firstInstance.MainDicomTags.SeriesDescription || 'No description',
              modality: modality,
              instanceCount: instances.length,
              imageIds: sortedInstances.map((instance: any) => getOrthancImageId(instance.ID))
            }

            study.series.push(series)
          }
        }

        patient.studies.push(study)
      }
      
      // Convert map to array
      patients.value = Array.from(patientMap.values())
      console.log('Finished loading data - patients:', patients.value.length)

      // Set default selection if available
      if (patients.value.length > 0) {
        currentPatientId.value = patients.value[0].id
        
        const firstPatient = patients.value[0]
        if (firstPatient.studies.length > 0) {
          currentStudyId.value = firstPatient.studies[0].id
          
          const firstStudy = firstPatient.studies[0]
          if (firstStudy.series.length > 0) {
            currentSeriesId.value = firstStudy.series[0].id
          }
        }
      }
      
    } catch (err) {
      console.error('Failed to load medical data:', err)
      error.value = err instanceof Error ? err.message : 'Unknown error loading data'
    } finally {
      loading.value = false
    }
  }

  function selectPatient(patientId: string) {
    currentPatientId.value = patientId
    
    // Reset current study and series
    const patient = patients.value.find(p => p.id === patientId)
    currentStudyId.value = patient && patient.studies.length > 0 ? patient.studies[0].id : null
    
    // Reset current series
    const study = patient?.studies.find(s => s.id === currentStudyId.value)
    currentSeriesId.value = study && study.series.length > 0 ? study.series[0].id : null
  }

  function selectStudy(studyId: string) {
    currentStudyId.value = studyId
    
    // Reset current series
    const patient = currentPatient.value
    const study = patient?.studies.find(s => s.id === studyId)
    currentSeriesId.value = study && study.series.length > 0 ? study.series[0].id : null
  }

  function selectSeries(seriesId: string) {
    currentSeriesId.value = seriesId
  }

  return {
    // State
    patients,
    loading,
    error,
    currentPatientId,
    currentStudyId,
    currentSeriesId,
    
    // Getters
    currentPatient,
    currentStudy,
    currentSeries,
    currentImageIds,
    
    // Actions
    loadAllData,
    selectPatient,
    selectStudy,
    selectSeries
  }
}) 