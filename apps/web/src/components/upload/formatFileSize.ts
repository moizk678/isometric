export function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(bytes < 10 * 1024 ? 1 : 0)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(bytes < 10 * 1024 * 1024 ? 1 : 0)} MB`;
}

export function fileTypeLabel(mimeType: string): string {
  if (mimeType === 'image/png') {
    return 'PNG';
  }
  if (mimeType === 'image/jpeg') {
    return 'JPEG';
  }
  return mimeType.replace('image/', '').toUpperCase();
}
