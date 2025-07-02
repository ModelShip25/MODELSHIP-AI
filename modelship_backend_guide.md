# ModelShip Backend — Developer Guide (Cursor-Ready)

> This guide is for **ModelShip's backend**, structured for development using **FastAPI**, **SAHI + YOLOX pipeline**, and **Supabase** for database + storage. This is the official structure and dev workflow.

---

## 🧰 Tech Stack Overview

| Component         | Stack / Tool          | Purpose                                     |
| ----------------- | --------------------- | ------------------------------------------- |
| Web Framework     | FastAPI               | REST API server                             |
| ML Pipeline       | SAHI + YOLOX          | Auto-labeling via image slicing + detection |
| Data Processing   | Pandas (optional)     | Validation, cleaning, CSV output            |
| Storage           | Supabase Storage      | Store uploaded and labeled images           |
| Database          | Supabase PostgreSQL   | Store image + annotation metadata           |
| Preview           | OpenCV, Pillow        | Draw bounding boxes                         |
| Model Runtime     | ONNXRuntime           | Run YOLOX in production                     |
| Annotation Export | JSON, CSV, YOLO, COCO | For AI/ML dataset training                  |

> 📌 Note: Supabase is **not** our backend. We use it **only for DB and storage** — our backend is entirely built with FastAPI.

---

## ✅ MVP Features

### 1. **Data Upload**

- Upload raw images or datasets
- Store them in Supabase Storage

### 2. **Data Cleaning**

- Detect and remove duplicates
- Validate formats (image resolution, type)

### 3. **Auto Labeling**

- Run image through YOLOX model (via SAHI)
- Output bounding boxes + class labels

### 4. **Preview**

- Visual preview of labeled image (with bounding boxes)
- Support for real-time label review before export

### 5. **Edit Mode (If Needed to edit data before saving)**

- Ability for user to adjust labels (box position, size, class)
- Updated preview and data reflected live

### 6. **Export**

- Final labeled dataset exported in multiple formats:
  - YOLO `.txt`
  - COCO JSON
  - CSV
  - ZIP with preview and raw images (optional)

### 7. **Storage & Retrieval**

- Labeled data and previews are stored for user download
- Users can revisit past jobs and re-export or edit

---

## 🔄 Workflow Breakdown

### ✅ Step-by-Step Flow

```text
[1] Upload: User uploads raw image(s) → /upload
     ↓
[2] Clean: Backend deduplicates and validates → /clean
     ↓
[3] Label: Pipeline runs YOLOX + SAHI → /label
     ↓
[4] Preview: Draw boxes on original image → /preview
     ↓
[5] Review: User checks output, edits if needed → (frontend/editor)
     ↓
[6] Export: System exports ZIP file with all annotations → /export
```

Each step handled by its own service and route.

---

## ✅ Final Project Root Structure

```
backend/
├── app/
│   ├── main.py                     # FastAPI entrypoint
│   ├── core/
│   │   ├── config.py               # App configs (.env loader)
│   │   └── utils.py                # Shared helpers
│   ├── models/                     # Pydantic & database schemas
│   │   ├── image.py
│   │   ├── annotation.py
│   │   └── user.py
│   ├── services/                   # Core business logic
│   │   ├── cleaning.py             # Duplicate removal, validation
│   │   ├── labeling.py             # Connects pipeline + output
│   │   ├── export.py               # YOLO, COCO, JSON, CSV
│   │   └── preview.py              # Draws boxes on images
│   ├── pipeline/                   # Auto-labeling pipeline
│   │   ├── __init__.py
│   │   ├── detector.py             # Loads YOLOX model
│   │   ├── sahi_wrapper.py         # Slicing + prediction logic
│   │   └── config.py               # Model paths, thresholds
│   ├── routes/                     # FastAPI route handlers
│   │   ├── upload.py
│   │   ├── clean.py
│   │   ├── label.py
│   │   ├── preview.py
│   │   └── export.py
│   └── storage/                    # Storage logic (local or Supabase)
│       ├── image_store.py
│       └── label_store.py
├── supabase/                       # SQL schema files for Supabase
│   ├── schema.sql
│   └── tables/
│       ├── images.sql
│       ├── annotations.sql
│       └── users.sql
├── .env                            # Model paths, DB URL, secrets
├── requirements.txt
└── README.md
```

> ⚡ Every feature must fit into this structure. No new folders unless added here.

...

