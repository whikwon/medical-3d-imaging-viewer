<template>
  <div class="control-overlay multiframe-overlay">
    <div class="overlay-header">
      <h4>Multiframe Controls</h4>
      <button @click="$emit('close')" class="overlay-close">×</button>
    </div>

    <div class="slider-container">
      <label>Frame:</label>
      <input
        type="range"
        :value="currentFrame"
        @input="updateCurrentFrame($event)"
        :min="0"
        :max="maxFrame"
      />
      <span>{{ currentFrame + 1 }} / {{ maxFrame + 1 }}</span>
    </div>
    <div class="player-controls">
      <button @click="$emit('togglePlayback')" class="control-btn">
        {{ isPlaying ? 'Pause' : 'Play' }}
      </button>
      <div class="speed-control">
        <label>Speed:</label>
        <input
          type="range"
          :value="playbackSpeed"
          @input="updatePlaybackSpeed($event)"
          min="1"
          max="30"
          step="1"
        />
        <span>{{ playbackSpeed }} fps</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Define props
const props = defineProps<{
  currentFrame: number
  maxFrame: number
  isPlaying: boolean
  playbackSpeed: number
}>()

// Define emits
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'update:currentFrame', value: number): void
  (e: 'update:playbackSpeed', value: number): void
  (e: 'frameChanged'): void
  (e: 'togglePlayback'): void
}>()

// Helper methods
function updateCurrentFrame(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:currentFrame', parseInt(target.value))
  emit('frameChanged')
}

function updatePlaybackSpeed(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:playbackSpeed', parseInt(target.value))
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

.multiframe-overlay {
  bottom: 20px;
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

.player-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 15px;
}

.speed-control {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.85em;
}

.speed-control input[type='range'] {
  width: 80px;
  background-color: rgba(255, 255, 255, 0.2);
}
</style>
