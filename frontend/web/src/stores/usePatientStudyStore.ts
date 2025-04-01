import { fetchPatients, fetchSeriesForStudy, fetchStudies } from '@/services/orthancService'
import type { Patient, Series, Study } from '@/types/orthanc'
import { defineStore } from 'pinia'

interface PatientStudyState {
  patients: Patient[]
  selectedPatient: Patient | null
  studies: (Study & { series?: Series[] })[]
  activeSeriesId: string | null
  loadingSeriesId: string | null
  loadingPatients: boolean
  loadingStudies: boolean
  patientError: string | null
  studyError: string | null
}

export const usePatientStudyStore = defineStore('patientStudy', {
  state: (): PatientStudyState => ({
    patients: [],
    selectedPatient: null,
    studies: [],
    activeSeriesId: null,
    loadingSeriesId: null,
    loadingPatients: false,
    loadingStudies: false,
    patientError: null,
    studyError: null,
  }),

  actions: {
    async fetchPatientsAction() {
      this.loadingPatients = true
      this.patientError = null
      try {
        this.patients = await fetchPatients()
      } catch (e) {
        this.patientError = 'Failed to load patients. Please try again.'
        console.error('Error loading patients:', e)
        this.patients = [] // Ensure patients is an empty array on error
      } finally {
        this.loadingPatients = false
      }
    },

    selectPatientAction(patient: Patient | null) {
      if (this.selectedPatient?.ID !== patient?.ID) {
        this.selectedPatient = patient
        this.studies = [] // Clear previous studies
        this.activeSeriesId = null // Clear active series
        this.studyError = null
        if (patient) {
          this.fetchStudiesForPatientAction(patient.ID)
        } else {
          // Handle case where patient is deselected (set to null)
          this.loadingStudies = false
        }
      }
    },

    async fetchStudiesForPatientAction(patientId: string) {
      this.loadingStudies = true
      this.studyError = null
      try {
        const allStudies = await fetchStudies()
        const patientStudies = allStudies.filter((study) => study.ParentPatient === patientId)

        // Load series for each study
        for (const study of patientStudies) {
          try {
            // Explicitly add series property
            ;(study as Study & { series?: Series[] }).series = await fetchSeriesForStudy(study.ID)
          } catch (e) {
            console.error(`Error loading series for study ${study.ID}:`, e)
            ;(study as Study & { series?: Series[] }).series = []
          }
        }
        this.studies = patientStudies
      } catch (e) {
        this.studyError = 'Failed to load studies'
        console.error('Error loading studies:', e)
        this.studies = []
      } finally {
        this.loadingStudies = false
      }
    },

    selectSeriesAction(series: Series | null) {
      if (series) {
        // Set loading state *before* emitting or triggering async actions in components
        this.loadingSeriesId = series.ID
        // Set active series *after* loading starts (or perhaps handled by VTKCanvas watching loadingSeriesId)
        // Let VTKCanvas handle the actual loading and setting activeSeriesId after load
        // This store just signals the *intent* to load/select a series.
      } else {
        this.activeSeriesId = null
        this.loadingSeriesId = null
      }
    },

    // Action called by VTKCanvas once loading is complete (or failed)
    setSeriesLoadingCompleteAction(seriesId: string | null, success: boolean) {
      if (this.loadingSeriesId === seriesId) {
        if (success) {
          this.activeSeriesId = seriesId
        } else {
          // Optionally handle failure case, maybe clear activeSeriesId or set an error
          console.error(`Failed to load series ${seriesId}`)
        }
        this.loadingSeriesId = null // Clear loading state regardless of success/failure
      }
    },

    // Optional: Action to clear the selected series manually if needed
    clearActiveSeriesAction() {
      this.activeSeriesId = null
      this.loadingSeriesId = null
    },
  },
})
