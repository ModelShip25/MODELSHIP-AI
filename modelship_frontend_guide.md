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

**Endpoint:** `POST /api/v1/upload`  
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

const response = await fetch(`${BACKEND_URL}/api/v1/upload`, {
  method: 'POST',
  body: formData,
});
const result: UploadResponse = await response.json();
```

### 2. Data Cleaning

**Endpoint:** `POST /api/v1/clean`  
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
const response = await fetch(`${BACKEND_URL}/api/v1/clean`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ image_ids: ['id1', 'id2'] }),
});
const result: CleanResponse = await response.json();
```

### 3. Auto-Labeling

**Endpoint:** `POST /api/v1/label`  
**Purpose:** Run object detection on cleaned images  

```typescript
interface LabelRequest {
  image_ids: string[];
  conf_thresh?: number;  // Optional confidence threshold
  nms_thresh?: number;   // Optional NMS threshold
}

interface BoundingBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

interface Annotation {
  id: string;
  image_id: string;
  class_name: string;
  confidence: number;
  bbox: BoundingBox;
  area: number;
  source: string;
}

interface LabelResponse {
  annotations: Annotation[];
  status: 'completed' | 'processing';
}

// Example usage
const response = await fetch(`${BACKEND_URL}/api/v1/label`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ image_ids: ['id1'] }),
});
const result: LabelResponse = await response.json();
```

### 4. Preview Generation

**Endpoint:** `GET /api/v1/preview/{image_id}`  
**Purpose:** Get preview image with drawn bounding boxes  

```typescript
// Example usage
const previewUrl = `${BACKEND_URL}/api/v1/preview/${imageId}`;
```

### 5. Label Editing

**Endpoint:** `PUT /api/v1/label/{annotation_id}`  
**Purpose:** Update existing annotations  

```typescript
interface EditAnnotationRequest {
  class_name?: string;
  bbox?: BoundingBox;
  confidence?: number;
}

// Example usage
const response = await fetch(`${BACKEND_URL}/api/v1/label/${annotationId}`, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    class_name: 'car',
    bbox: { x_min: 100, y_min: 100, x_max: 300, y_max: 250 }
  }),
});
```

### 6. Export

**Endpoint:** `POST /api/v1/export`  
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
const response = await fetch(`${BACKEND_URL}/api/v1/export`, {
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
  filename: string;
  file_path: string;
  file_size: number;
  width: number;
  height: number;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  preview_path?: string;
  created_at: string;
  updated_at: string;
  user_id?: string;
}
```

### Annotations Table
```typescript
interface Annotation {
  id: string;
  image_id: string;
  class_name: string;
  confidence: number;
  bbox: BoundingBox;
  area: number;
  source: string;
  created_at: string;
  updated_at: string;
  user_id?: string;
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
The backend provides status updates through polling. Here's how to implement it:

```typescript
interface JobStatus {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  error?: string;
}

const pollJobStatus = async (jobId: string, interval = 1000): Promise<JobStatus> => {
  while (true) {
    const response = await fetch(`${BACKEND_URL}/api/v1/jobs/${jobId}`);
    const status: JobStatus = await response.json();
    
    if (status.status === 'completed' || status.status === 'failed') {
      return status;
    }
    
    await new Promise(resolve => setTimeout(resolve, interval));
  }
};

// Example usage:
const status = await pollJobStatus('job-123');
if (status.status === 'completed') {
  // Handle completion
} else {
  // Handle failure
  console.error(status.error);
}
```

## 🔐 Error Handling

The API uses standard HTTP status codes:

- 200: Success
- 400: Bad Request (invalid parameters)
- 401: Unauthorized (invalid or missing authentication)
- 403: Forbidden (insufficient permissions)
- 404: Not Found
- 500: Internal Server Error

Error responses follow this format:

```typescript
interface ErrorResponse {
  error: {
    message: string;
    code?: string;
    details?: any;
  }
}
```

Example error handling:
```typescript
try {
  const response = await fetch(`${BACKEND_URL}/api/v1/upload`, {
    method: 'POST',
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error.message);
  }
  
  const result = await response.json();
  // Handle success
} catch (error) {
  // Handle error
  console.error('Upload failed:', error.message);
}
```

## 📝 Environment Variables

Required environment variables for frontend:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your-project-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## 🚀 Getting Started

1. Install dependencies:
```bash
npm install @supabase/supabase-js
```

2. Set up environment variables in `.env.local`

3. Initialize Supabase client:
```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);
```

4. Start making API calls following the examples above! 