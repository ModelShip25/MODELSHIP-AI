Absolutely — here's your **rewritten and fully corrected development plan**, made for solo backend dev (you) + Cursor AI support.

---

# ✅ ModelShip Backend — Phase-by-Phase Development Guide (Solo Dev + Cursor)

This guide is your step-by-step plan to build ModelShip’s backend. Every phase builds logically from the last. Each step includes its exact files, purpose, and output so you don’t get lost.

---

## 🧱 Phase 1: Entrypoint + Upload System (Boot + Input)

> First, make the app run and handle uploads. This unlocks all other services.

### 📁 Affected Files

* `main.py`
* `routes/upload.py`
* `storage/image_store.py`
* `models/image.py`

### ✅ Goals

* Set up `FastAPI` server
* Enable CORS
* Include `upload` route
* Accept images via `POST`
* Store uploaded images (local or Supabase)
* Return basic image metadata (ID, path, filename)

### 🧪 Test

* Run `uvicorn app.main:app --reload`
* Use `curl` or Postman to send an image and get a response

---

## 🧼 Phase 2: Data Cleaning (Validation & Duplicates)

> Clean data before passing to the pipeline.

### 📁 Affected Files

* `routes/clean.py`
* `services/cleaning.py`

### ✅ Goals

* Remove duplicate images using hash or pixel similarity
* Validate image types and sizes
* Return clean image list

---

## 🤖 Phase 3: Auto Labeling Pipeline (YOLOX + SAHI)

> Core of the product: auto-label the images using object detection.

### 📁 Affected Files

* `pipeline/detector.py`
* `pipeline/sahi_wrapper.py`
* `pipeline/config.py`
* `services/labeling.py`
* `routes/label.py`

### ✅ Goals

* Load YOLOX model (ONNX)
* Slice images using SAHI
* Predict bounding boxes and labels
* Save raw output to memory or storage

---

## 👁️ Phase 4: Preview Generation (Reviewable Visual Output)

> Let users review how their data was labeled.

### 📁 Affected Files

* `services/preview.py`
* `routes/preview.py`

### ✅ Goals

* Draw bounding boxes on images (OpenCV or Pillow)
* Save preview image
* Return preview image path or displayable link

---

## 📝 Phase 5: Edit Mode (Optional Label Tweaks)

> Allow manual correction before export (for team use).

### 📁 Affected Files

* `models/annotation.py`
* `routes/label.py`
* Possibly: `services/editor.py` or extend `labeling.py`

### ✅ Goals

* Accept user edits to label boxes or class names
* Update stored annotation records in real time

---

## 📦 Phase 6: Export System (YOLO, COCO, CSV, ZIP)

> Export final labeled datasets in formats for AI training.

### 📁 Affected Files

* `services/export.py`
* `routes/export.py`

### ✅ Goals

* Export:

  * YOLO `.txt`
  * COCO JSON
  * CSV
  * ZIP with raw images + previews + metadata
* Return download link or file

---

## 💾 Phase 7: Supabase Metadata Storage

> Record job history, image data, and user metadata.

### 📁 Affected Files

* `models/image.py`, `annotation.py`, `user.py`
* `supabase/schema.sql`
* `storage/image_store.py`, `label_store.py`

### ✅ Goals

* Insert metadata into Supabase after upload/label
* Enable “job history” and dataset lookup later

---

## 🚀 Final Phase: Testing + Deployment

> Polish and make the app production-ready.

### ✅ Goals

* Run through entire workflow from upload → export
* Write basic tests (optional)
* Deploy on:

  * Railway
  * Render
  * Docker (if needed)
* Connect frontend to API

---

## 📊 Phase Summary Table

| Phase | Feature                | What You Build                            |
| ----- | ---------------------- | ----------------------------------------- |
| 1     | Entrypoint + Upload    | `main.py`, `upload.py`, `image_store.py`  |
| 2     | Data Cleaning          | `cleaning.py`, `clean.py`                 |
| 3     | Auto-Labeling          | `YOLOX + SAHI` pipeline files             |
| 4     | Preview Generator      | `preview.py`, `preview route`             |
| 5     | Edit Labels (optional) | Extend `label.py`                         |
| 6     | Export Formats         | `export.py`, `export route`               |
| 7     | Supabase Metadata      | `models/`, `schema.sql`, `label_store.py` |
| 8     | Testing & Deploy       | Full flow testing                         |

---

### 🧠 Extra Tips

* Each phase = 1 GitHub commit
* Push often. Use Cursor to autogenerate helper functions inside each module
* Stick to root folder structure exactly as defined