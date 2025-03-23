<template>
  <div class="control-overlay volume-overlay">
    <div class="overlay-header">
      <h4>Volume Controls</h4>
      <button @click="$emit('close')" class="overlay-close">×</button>
    </div>

    <div class="sliders">
      <div class="slider-container">
        <label>Window Width:</label>
        <input
          type="range"
          :value="windowWidth"
          @input="updateWindowWidth($event)"
          :min="1"
          :max="windowWidthMax"
        />
        <span>{{ windowWidth }}</span>
      </div>

      <div class="slider-container">
        <label>Window Center:</label>
        <input
          type="range"
          :value="windowCenter"
          @input="updateWindowCenter($event)"
          :min="windowCenterMin"
          :max="windowCenterMax"
        />
        <span>{{ windowCenter }}</span>
      </div>
    </div>

    <div class="slice-controls">
      <h4>Slice Navigation</h4>
      <div class="slider-container">
        <label>Axial (K):</label>
        <input
          type="range"
          :value="kSlice"
          @input="updateKSlice($event)"
          :min="kExtentMin"
          :max="kExtentMax"
        />
        <span>{{ kSlice }}</span>
      </div>

      <div class="slider-container">
        <label>Coronal (J):</label>
        <input
          type="range"
          :value="jSlice"
          @input="updateJSlice($event)"
          :min="jExtentMin"
          :max="jExtentMax"
        />
        <span>{{ jSlice }}</span>
      </div>

      <div class="slider-container">
        <label>Sagittal (I):</label>
        <input
          type="range"
          :value="iSlice"
          @input="updateISlice($event)"
          :min="iExtentMin"
          :max="iExtentMax"
        />
        <span>{{ iSlice }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Define props
const props = defineProps<{
  windowWidth: number
  windowCenter: number
  windowWidthMax: number
  windowCenterMin: number
  windowCenterMax: number
  iSlice: number
  jSlice: number
  kSlice: number
  iExtentMin: number
  iExtentMax: number
  jExtentMin: number
  jExtentMax: number
  kExtentMin: number
  kExtentMax: number
}>()

// Define emits
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'update:windowWidth', value: number): void
  (e: 'update:windowCenter', value: number): void
  (e: 'update:iSlice', value: number): void
  (e: 'update:jSlice', value: number): void
  (e: 'update:kSlice', value: number): void
  (e: 'windowLevelChanged'): void
  (e: 'slicesChanged'): void
}>()

// Helper methods
function updateWindowWidth(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:windowWidth', parseInt(target.value))
  emit('windowLevelChanged')
}

function updateWindowCenter(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:windowCenter', parseInt(target.value))
  emit('windowLevelChanged')
}

function updateISlice(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:iSlice', parseInt(target.value))
  emit('slicesChanged')
}

function updateJSlice(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:jSlice', parseInt(target.value))
  emit('slicesChanged')
}

function updateKSlice(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:kSlice', parseInt(target.value))
  emit('slicesChanged')
}
</script>

<style scoped>
.control-overlay {
  position: absolute;
  background-color: rgba(33, 33, 33, 0.8);
  color: white;
  border-radius: 6px;
  padding: 15px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
  z-index: 20;
  max-width: 350px;
  backdrop-filter: blur(4px);
}

.volume-overlay {
  top: 20px;
  right: 20px;
}

.overlay-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.overlay-header h4 {
  margin: 0;
  font-size: 1em;
}

.overlay-close {
  background: none;
  color: white;
  border: none;
  font-size: 20px;
  cursor: pointer;
  padding: 0 5px;
}

.overlay-close:hover {
  color: #ff5252;
}

.control-btn {
  background-color: #3f8cff;
  transition: background-color 0.2s;
  padding: 6px 12px;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.control-btn:hover {
  background-color: #2b6fc5;
}

.sliders,
.slice-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.slice-controls {
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  padding-top: 10px;
  margin-top: 10px;
}

.slice-controls h4 {
  margin: 0 0 5px 0;
  font-size: 0.9em;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.9em;
}

.slider-container label {
  width: 90px;
  font-weight: bold;
}

.slider-container input[type='range'] {
  flex: 1;
  background-color: rgba(255, 255, 255, 0.2);
}

.slider-container span {
  width: 40px;
  text-align: right;
}
</style>
