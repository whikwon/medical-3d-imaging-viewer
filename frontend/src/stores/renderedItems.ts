import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useMedicalDataStore } from './medicalData'
import type { Series } from './medicalData'

export interface RenderedItem {
  id: string;
  position: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  seriesId: string;
  studyId: string;
  patientId: string;
  patientName: string;
  studyDesc: string;
  seriesDesc: string;
  modality: string;
  imageIds: string[];
}

export const useRenderedItemsStore = defineStore('renderedItems', () => {
  // State
  const renderedItems = ref<RenderedItem[]>([])
  const draggingItem = ref<string | null>(null)
  const medicalDataStore = useMedicalDataStore()

  // Getters
  const getItemById = (id: string) => {
    return renderedItems.value.find(item => item.id === id)
  }

  // Actions
  function addRenderedItem(seriesId: string) {
    // Find the series in the medical data store
    const patient = medicalDataStore.patients.find(p => 
      p.studies.some(s => s.series.some(sr => sr.id === seriesId))
    )
    
    if (!patient) {
      console.error(`Series with ID ${seriesId} not found`)
      return
    }
    
    const study = patient.studies.find(s => s.series.some(sr => sr.id === seriesId))
    if (!study) return
    
    const series = study.series.find(sr => sr.id === seriesId)
    if (!series) return

    // Create a new rendered item
    const newItem: RenderedItem = {
      id: `rendered-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      position: {
        x: 10,
        y: 10,
        width: 400,
        height: 400
      },
      seriesId: series.id,
      studyId: study.id,
      patientId: patient.id,
      patientName: patient.name,
      studyDesc: study.description,
      seriesDesc: series.description,
      modality: series.modality,
      imageIds: [...series.imageIds]
    }

    renderedItems.value.push(newItem)
    return newItem.id
  }

  function removeRenderedItem(itemId: string) {
    const index = renderedItems.value.findIndex(item => item.id === itemId)
    if (index !== -1) {
      renderedItems.value.splice(index, 1)
    }
  }

  function updateItemPosition(itemId: string, position: { x: number, y: number, width?: number, height?: number }) {
    const item = renderedItems.value.find(item => item.id === itemId)
    if (item) {
      item.position = {
        ...item.position,
        ...position
      }
    }
  }

  function setDraggingItem(itemId: string | null) {
    draggingItem.value = itemId
  }

  return {
    renderedItems,
    draggingItem,
    getItemById,
    addRenderedItem,
    removeRenderedItem,
    updateItemPosition,
    setDraggingItem
  }
}) 