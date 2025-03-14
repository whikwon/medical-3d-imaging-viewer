<template>
  <div class="multi-view-renderer">
    <div class="viewport-container" ref="containerRef">
      <div
        v-for="item in renderedItems"
        :key="item.id"
        class="viewport-item"
        :style="{
          left: `${item.position.x}px`,
          top: `${item.position.y}px`,
          width: `${item.position.width}px`,
          height: `${item.position.height}px`,
        }"
        :class="{ dragging: isDragging && draggingItem === item.id }"
      >
        <div
          class="viewport-header"
          @mousedown="startDragging($event, item.id)"
          @touchstart="startDragging($event, item.id)"
        >
          <div class="viewport-info">
            <div class="viewport-title">{{ item.patientName }}</div>
            <div class="viewport-subtitle">
              {{ item.studyDesc }} - {{ item.seriesDesc }} ({{ item.modality }})
            </div>
          </div>
          <div class="viewport-controls">
            <button class="remove-btn" @click="removeItem(item.id)">×</button>
          </div>
        </div>
        <div class="viewport-content">
          <!-- Use OrthogonalViewer for CT data and standard viewer for other modalities -->
          <OrthogonalViewer
            v-if="item.modality === 'CT'"
            :imageIds="item.imageIds"
            :itemId="item.id"
            :modality="item.modality"
          />
          <AngioView v-else :imageIds="item.imageIds" :viewportId="item.id" />
        </div>
        <!-- Resize handles -->
        <div
          class="resize-handle resize-handle-se"
          @mousedown="startResizing($event, item.id, 'se')"
          @touchstart="startResizing($event, item.id, 'se')"
        ></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import AngioView from './AngioView.vue'
import OrthogonalViewer from './OrthogonalViewer.vue'
import { useRenderedItemsStore } from '../stores/renderedItems'

const renderedItemsStore = useRenderedItemsStore()
const renderedItems = computed(() => renderedItemsStore.renderedItems)

const containerRef = ref<HTMLElement | null>(null)
const isDragging = ref(false)
const isResizing = ref(false)
const draggingItem = ref<string | null>(null)
const resizingItem = ref<string | null>(null)
const resizeDirection = ref<string | null>(null)
const dragOffset = ref({ x: 0, y: 0 })
const initialSize = ref({ width: 0, height: 0 })
const initialPos = ref({ x: 0, y: 0 })

// Drag and resize handling
function startDragging(event: MouseEvent | TouchEvent, itemId: string) {
  // Ignore if right click
  if (event instanceof MouseEvent && event.button !== 0) return

  event.preventDefault()

  const clientX = event instanceof MouseEvent ? event.clientX : event.touches[0].clientX
  const clientY = event instanceof MouseEvent ? event.clientY : event.touches[0].clientY

  const item = renderedItemsStore.getItemById(itemId)
  if (!item) return

  isDragging.value = true
  draggingItem.value = itemId
  renderedItemsStore.setDraggingItem(itemId)

  // Calculate the offset of the click from the element's top-left corner
  dragOffset.value = {
    x: clientX - item.position.x,
    y: clientY - item.position.y,
  }

  document.addEventListener('mousemove', onDragMove)
  document.addEventListener('touchmove', onDragMove)
  document.addEventListener('mouseup', stopDragging)
  document.addEventListener('touchend', stopDragging)
}

function startResizing(event: MouseEvent | TouchEvent, itemId: string, direction: string) {
  // Ignore if right click
  if (event instanceof MouseEvent && event.button !== 0) return

  event.preventDefault()

  const item = renderedItemsStore.getItemById(itemId)
  if (!item) return

  isResizing.value = true
  resizingItem.value = itemId
  resizeDirection.value = direction

  // Store initial size and position
  initialSize.value = {
    width: item.position.width,
    height: item.position.height,
  }

  initialPos.value = {
    x: item.position.x,
    y: item.position.y,
  }

  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('touchmove', onResizeMove)
  document.addEventListener('mouseup', stopResizing)
  document.addEventListener('touchend', stopResizing)
}

function onDragMove(event: MouseEvent | TouchEvent) {
  if (!isDragging.value || !draggingItem.value) return

  const clientX = event instanceof MouseEvent ? event.clientX : event.touches[0].clientX
  const clientY = event instanceof MouseEvent ? event.clientY : event.touches[0].clientY

  // Calculate new position
  const newX = clientX - dragOffset.value.x
  const newY = clientY - dragOffset.value.y

  // Update the position in the store
  renderedItemsStore.updateItemPosition(draggingItem.value, { x: newX, y: newY })
}

function onResizeMove(event: MouseEvent | TouchEvent) {
  if (!isResizing.value || !resizingItem.value) return

  const clientX = event instanceof MouseEvent ? event.clientX : event.touches[0].clientX
  const clientY = event instanceof MouseEvent ? event.clientY : event.touches[0].clientY

  const container = containerRef.value
  if (!container) return

  const containerRect = container.getBoundingClientRect()

  if (resizeDirection.value === 'se') {
    // Calculate new width and height
    const newWidth = Math.max(200, clientX - containerRect.left - initialPos.value.x)
    const newHeight = Math.max(200, clientY - containerRect.top - initialPos.value.y)

    // Update the size in the store
    renderedItemsStore.updateItemPosition(resizingItem.value, {
      x: initialPos.value.x,
      y: initialPos.value.y,
      width: newWidth,
      height: newHeight,
    })
  }
}

function stopDragging() {
  if (isDragging.value) {
    isDragging.value = false
    draggingItem.value = null
    renderedItemsStore.setDraggingItem(null)

    document.removeEventListener('mousemove', onDragMove)
    document.removeEventListener('touchmove', onDragMove)
    document.removeEventListener('mouseup', stopDragging)
    document.removeEventListener('touchend', stopDragging)
  }
}

function stopResizing() {
  if (isResizing.value) {
    isResizing.value = false
    resizingItem.value = null
    resizeDirection.value = null

    document.removeEventListener('mousemove', onResizeMove)
    document.removeEventListener('touchmove', onResizeMove)
    document.removeEventListener('mouseup', stopResizing)
    document.removeEventListener('touchend', stopResizing)
  }
}

function removeItem(itemId: string) {
  renderedItemsStore.removeRenderedItem(itemId)
}

// Clean up event listeners when the component is unmounted
onUnmounted(() => {
  stopDragging()
  stopResizing()
})

// Watch for changes in rendered items to ensure proper initialization of views
watch(
  () => renderedItems.value,
  (items) => {
    // Find CT items and ensure they're properly initialized
    const ctItems = items.filter((item) => item.modality === 'CT')
    if (ctItems.length > 0) {
      console.log(`Detected ${ctItems.length} CT volumes to render with orthogonal views`)
    }
  },
)
</script>

<style scoped>
.multi-view-renderer {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.viewport-container {
  position: relative;
  width: 100%;
  height: 100%;
  background-color: #f0f0f0;
}

.viewport-item {
  position: absolute;
  display: flex;
  flex-direction: column;
  background-color: white;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  min-width: 200px;
  min-height: 200px;
  transition: box-shadow 0.2s ease;
  z-index: 1;
}

.viewport-item.dragging {
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
  opacity: 0.8;
  z-index: 10;
}

.viewport-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background-color: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
  cursor: move;
  user-select: none;
}

.viewport-info {
  overflow: hidden;
}

.viewport-title {
  font-weight: 500;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.viewport-subtitle {
  font-size: 0.75rem;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.viewport-controls {
  display: flex;
  align-items: center;
}

.remove-btn {
  border: none;
  background: none;
  color: #666;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.remove-btn:hover {
  color: #e53935;
  background-color: rgba(0, 0, 0, 0.05);
}

.viewport-content {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.resize-handle {
  position: absolute;
  width: 12px;
  height: 12px;
  background-color: #2196f3;
  border-radius: 50%;
  z-index: 20;
}

.resize-handle-se {
  bottom: 4px;
  right: 4px;
  cursor: nwse-resize;
}
</style>
