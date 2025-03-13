declare module '@cornerstonejs/core' {
  export function init(): void;
  
  export class RenderingEngine {
    constructor(id: string);
    enableElement(viewportInput: any): void;
    getViewport(viewportId: string): any;
  }
  
  export namespace Enums {
    export enum ViewportType {
      STACK = 'STACK',
      PERSPECTIVE = 'PERSPECTIVE',
      ORTHOGRAPHIC = 'ORTHOGRAPHIC'
    }
    
    export enum MetadataModules {
      IMAGE_PIXEL = 'imagePixel',
      VOI_LUT = 'voiLutModule',
      SOP_COMMON = 'sopCommonModule'
    }
  }
  
  export namespace Types {
    export interface IStackViewport {
      setStack(imageIds: string[]): Promise<void>;
      getCurrentImageIdIndex(): number;
      getImageIds(): string[];
      setImageIdIndex(index: number): void;
      render(): void;
      getImageData(): any;
    }
    
    export type Point3 = [number, number, number];
  }
  
  export namespace metaData {
    export function get(metadataType: string, imageId: string): any;
  }
  
  export function getRenderingEngine(id: string): RenderingEngine | undefined;
}

declare module '@cornerstonejs/tools' {
  export function addTool(tool: any): void;
  
  export class PanTool {
    static toolName: string;
  }
  
  export class WindowLevelTool {
    static toolName: string;
  }
  
  export class StackScrollTool {
    static toolName: string;
  }
  
  export class ZoomTool {
    static toolName: string;
  }
  
  export namespace ToolGroupManager {
    export function createToolGroup(toolGroupId: string): any;
  }
  
  export namespace Enums {
    export enum MouseBindings {
      Primary = 1,
      Secondary = 2,
      Auxiliary = 4,
      Wheel = 8
    }
  }
}

declare module '@cornerstonejs/dicom-image-loader' {
  export function init(): void;
  
  export namespace wadouri {
    export function parseImageId(imageId: string): { url: string };
    export const dataSetCacheManager: {
      get: (url: string) => any;
    };
    export function makeXHR(): (xhr: XMLHttpRequest) => XMLHttpRequest;
  }
} 