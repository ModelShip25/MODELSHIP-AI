# ModelShip Frontend Developer Guide

> This guide provides comprehensive documentation for frontend developers to integrate with the ModelShip backend API. The backend is built with FastAPI and uses Supabase for storage and database operations.

## 🔑 Getting Started

### Backend Base URLs
```typescript
const BACKEND_URL = 'http://localhost:8000'  // Development
const SUPABASE_URL = process.env.SUPABASE_URL
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY
```

### Authentication
The application uses Supabase for authentication. Initialize the Supabase client in your frontend:

```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
```

## 📚 API Endpoints

### 1. Image Upload

**Endpoint:** `POST /upload`  
**Purpose:** Upload images for processing  

```typescript
interface UploadResponse {
  id: string;
  filename: string;
  file_path: string;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
}

// Example usage
const formData = new FormData();
formData.append('file', imageFile);

const response = await fetch(`${BACKEND_URL}/upload`, {
  method: 'POST',
  body: formData,
});
const result: UploadResponse = await response.json();
```

### 2. Data Cleaning

**Endpoint:** `POST /clean`  
**Purpose:** Clean and validate uploaded images  

```typescript
interface CleanRequest {
  image_ids: string[];
}

interface CleanResponse {
  cleaned_images: {
    id: string;
    status: string;
    duplicate_of?: string;
  }[];
}

// Example usage
const response = await fetch(`${BACKEND_URL}/clean`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ image_ids: ['id1', 'id2'] }),
});
const result: CleanResponse = await response.json();
```

### 3. Auto-Labeling

**Endpoint:** `POST /label`  
**Purpose:** Run object detection on cleaned images  

```typescript
interface LabelRequest {
  image_ids: string[];
  conf_thresh?: number;  // Optional confidence threshold
  nms_thresh?: number;   // Optional NMS threshold
}

interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface Annotation {
  id: string;
  image_id: string;
  label: string;
  confidence: number;
  bbox: BoundingBox;
}

interface LabelResponse {
  annotations: Annotation[];
  status: 'completed' | 'processing';
}

// Example usage
const response = await fetch(`${BACKEND_URL}/label`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ image_ids: ['id1'] }),
});
const result: LabelResponse = await response.json();
```

### 4. Preview Generation

**Endpoint:** `GET /preview/{image_id}`  
**Purpose:** Get preview image with drawn bounding boxes  

```typescript
// Example usage
const previewUrl = `${BACKEND_URL}/preview/${imageId}`;
```

### 5. Label Editing

**Endpoint:** `PUT /label/{annotation_id}`  
**Purpose:** Update existing annotations  

```typescript
interface EditAnnotationRequest {
  label?: string;
  bbox?: BoundingBox;
  confidence?: number;
}

// Example usage
const response = await fetch(`${BACKEND_URL}/label/${annotationId}`, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    label: 'car',
    bbox: { x: 100, y: 100, width: 200, height: 150 }
  }),
});
```

### 6. Export

**Endpoint:** `POST /export`  
**Purpose:** Export labeled dataset in various formats  

```typescript
interface ExportRequest {
  image_ids: string[];
  format: 'yolo' | 'coco' | 'csv';
  include_images?: boolean;
  include_previews?: boolean;
}

interface ExportResponse {
  download_url: string;
  format: string;
  expires_at: string;
}

// Example usage
const response = await fetch(`${BACKEND_URL}/export`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    image_ids: ['id1', 'id2'],
    format: 'coco',
    include_images: true
  }),
});
const result: ExportResponse = await response.json();
```

## 📊 Database Schema

### Images Table
```typescript
interface Image {
  id: string;
  user_id: string;
  filename: string;
  file_path: string;
  file_size: number;
  width: number;
  height: number;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
}
```

### Annotations Table
```typescript
interface Annotation {
  id: string;
  image_id: string;
  label: string;
  confidence: number;
  bbox: BoundingBox;
  created_at: string;
  updated_at: string;
  reviewed: boolean;
  reviewer_id?: string;
}
```

## 🔄 Workflow Integration

### Typical Frontend Flow

1. **Upload Images**
   ```typescript
   // 1. Upload images
   const uploadedImages = await uploadImages(files);
   
   // 2. Clean uploaded images
   const cleanedImages = await cleanImages(uploadedImages.map(img => img.id));
   
   // 3. Start labeling
   const labelingJob = await startLabeling(cleanedImages.map(img => img.id));
   
   // 4. Poll for completion
   const labelingResult = await pollLabelingStatus(labelingJob.id);
   
   // 5. Show previews
   const previews = await getPreviewUrls(labelingResult.image_ids);
   
   // 6. Export when ready
   const exportUrl = await exportDataset({
     image_ids: labelingResult.image_ids,
     format: 'coco'
   });
   ```

### Real-time Updates
The backend provides status updates through the response status. Implement polling for long-running operations:

```typescript
const pollStatus = async (jobId: string, interval = 1000): Promise<JobResult> => {
  while (true) {
    const response = await fetch(`${BACKEND_URL}/jobs/${jobId}`);
    const result = await response.json();
    
    if (result.status === 'completed' || result.status === 'failed') {
      return result;
    }
    
    await new Promise(resolve => setTimeout(resolve, interval));
  }
};
```

## 🎨 UI Components

Recommended component structure:

```
src/
├── components/
│   ├── Upload/
│   │   ├── DropZone.tsx
│   │   └── ProgressBar.tsx
│   ├── Preview/
│   │   ├── ImageGrid.tsx
│   │   └── BoundingBoxOverlay.tsx
│   ├── Editor/
│   │   ├── LabelEditor.tsx
│   │   └── BBoxEditor.tsx
│   └── Export/
│       ├── FormatSelector.tsx
│       └── DownloadButton.tsx
├── services/
│   ├── api.ts
│   └── supabase.ts
└── hooks/
    ├── useUpload.ts
    ├── useLabelJob.ts
    └── useExport.ts
```

## 🔒 Error Handling

The backend returns standard HTTP status codes:

- `400`: Bad Request - Invalid parameters
- `401`: Unauthorized - Authentication required
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Resource doesn't exist
- `500`: Internal Server Error

Example error handling:

```typescript
interface ApiError {
  code: string;
  message: string;
  details?: any;
}

const handleApiError = (error: ApiError) => {
  switch (error.code) {
    case 'invalid_file_type':
      return 'Please upload only JPG, PNG, or GIF files.';
    case 'file_too_large':
      return 'File size exceeds the 10MB limit.';
    default:
      return 'An unexpected error occurred. Please try again.';
  }
};
```

## 📱 Responsive Design Guidelines

The backend returns image dimensions and preview URLs optimized for different screen sizes:

```typescript
interface PreviewUrls {
  small: string;   // 320px width
  medium: string;  // 640px width
  large: string;   // 1280px width
  original: string;
}
```

## 🚀 Performance Considerations

1. **Large File Uploads**
   - Use chunked uploads for files > 10MB
   - Show progress indicators
   - Handle network interruptions

2. **Preview Loading**
   - Implement lazy loading
   - Use appropriate preview sizes
   - Cache previews locally

3. **Real-time Updates**
   - Use exponential backoff for polling
   - Consider WebSocket upgrade in future

## 🧪 Testing

Recommended testing setup:

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock API responses
const mockApiResponse = {
  id: 'test-id',
  status: 'completed',
  // ... other fields
};

// Example test
test('uploads image and shows preview', async () => {
  render(<UploadComponent />);
  
  const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
  const input = screen.getByLabelText(/upload/i);
  
  await userEvent.upload(input, file);
  
  await waitFor(() => {
    expect(screen.getByAltText(/preview/i)).toBeInTheDocument();
  });
});
```

## 📚 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Supabase Documentation](https://supabase.io/docs)
- [YOLOX Documentation](https://github.com/Megvii-BaseDetection/YOLOX)
- [SAHI Documentation](https://github.com/obss/sahi)

## 🤝 Support

For backend-related issues or questions:
1. Check the error response for detailed information
2. Ensure all required parameters are provided
3. Verify data types match the TypeScript interfaces
4. Contact the backend team with specific error codes and request payloads 