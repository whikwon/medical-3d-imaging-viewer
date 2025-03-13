declare module '../helpers/cornerstone' {
  export function convertMultiframeImageIds(imageIds: string[]): string[];
  export function prefetchMetadataInformation(imageIds: string[]): Promise<void>;
  export function htmlSetup(document: Document): { element: HTMLElement };
  export function addButtonToToolbar(options: { title: string; onClick: () => void }): void;
} 