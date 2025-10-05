# GCS Integration Documentation

## Overview

The web video annotator is now fully integrated with Google Cloud Storage (GCS) for video streaming and annotation storage.

## Features

### 1. Video Browser
- Browse all videos from a GCS path
- Visual status indicators:
  - ✓ **GREEN**: Labeled (has complete annotations)
  - ● **YELLOW**: In Progress (has draft annotations)
  - ○ **GRAY**: Not Started (no annotations)
- Progress tracking (e.g., "5 of 12 videos labeled - 41%")
- Filter by status: All / Labeled / Unlabeled / In Progress
- "Next Unlabeled" button to jump to first unlabeled video
- Refresh button to reload video list
- Customizable GCS path input

### 2. Annotation Preview
- View existing annotations before editing
- Timeline visualization with colored segments
- List view with all segment details
- Summary stats (segment count, total duration)
- "Edit" button to open full annotator
- "Delete All" button to clear annotations

### 3. GCS-Integrated Annotator
- Streams videos directly from GCS (signed URLs, 1-hour expiry)
- Loads existing annotations automatically
- Auto-saves annotations to GCS (2-second debounce)
- Save status indicator:
  - ✓ All changes saved
  - ● Unsaved changes
  - ↻ Saving...
  - ⚠ Save failed (with retry button)
- Manual "Save Now" button to force immediate save
- Back button with unsaved changes warning

### 4. Autosave Manager
- **Debouncing**: 2-second delay after last edit
- **Retry Logic**: 3 attempts with exponential backoff (1s, 2s, 4s)
- **Queue System**: Serializes concurrent saves
- **Atomic Writes**: Writes to temp file, then renames
- **Conflict Detection**: Warns if annotations modified elsewhere
- **Browser Close Warning**: Alerts if unsaved changes exist

### 5. Storage Pattern
- Videos: `gs://buildai-dataset/finetune_dataset/[path]/video.mp4`
- Annotations: `gs://buildai-dataset/finetune_dataset/[path]/video.jsonl`
- Name matching: Same base name, different extension

### 6. Annotation Format
```json
{
  "cutSegments": [
    {
      "start": "MM:SS",
      "end": "MM:SS",
      "label": "label_name",
      "description": "text"
    }
  ]
}
```

## Setup

### 1. Install Dependencies
```bash
npm install
```

### 2. Authenticate with GCP
```bash
gcloud auth application-default login
```

### 3. Configure Environment
Create `.env.local`:
```
GCP_PROJECT_ID=data-470400
GCS_BUCKET=buildai-dataset
GCS_VIDEO_PATH=finetune_dataset/test
```

### 4. Start the App
```bash
npm run dev
# Open http://localhost:3000
```

## Usage Workflow

### 1. Browse Videos
- App opens to video browser
- See all videos with status indicators
- Use filters to find specific videos
- Progress bar shows completion percentage

### 2. Select Video
- Click any video card to see preview
- Preview shows existing annotations (if any)
- Or shows "No annotations yet" with "Start Labeling" button

### 3. Annotate
- Click "Edit" or "Start Labeling"
- Video streams from GCS instantly
- Existing annotations load automatically
- Use keyboard shortcuts to mark segments:
  - `I` = Mark IN point
  - `O` = Mark OUT point
  - Fill label and description
  - `Enter` = Commit segment
- Annotations auto-save to GCS (watch status indicator)

### 4. Navigate
- Click "Back" to return to browser
- If unsaved changes, prompted to save first
- Video list refreshes to show updated status

### 5. Review & Edit
- Browse mode shows all videos with status
- Click any video to preview annotations
- Click "Edit" to modify existing annotations
- Click "Delete All" to clear (with confirmation)

## API Endpoints

### `GET /api/gcs/list-videos?path={gcsPath}`
- Lists all videos from GCS path
- Returns: `{ videos: VideoInfo[] }`
- Includes signed URLs and annotation status

### `POST /api/gcs/signed-url`
- Generates new signed URL for a video
- Input: `{ videoPath: string }`
- Output: `{ signedUrl: string }`

### `GET /api/gcs/annotations?videoPath={videoPath}`
- Loads annotations for a video
- Returns: `{ annotation: GCSAnnotation }`
- 404 if no annotations exist

### `POST /api/gcs/annotations`
- Saves annotations for a video
- Input: `{ videoPath: string, annotation: GCSAnnotation }`
- Output: `{ success: true }`

## Error Handling

### Auth Errors
- Message: "GCS authentication failed. Run: gcloud auth application-default login"
- Action: Reauthenticate with gcloud CLI

### Network Errors
- Auto-retry with exponential backoff (3 attempts)
- Status indicator shows retry progress
- Manual retry button appears on failure

### Save Conflicts
- Detects if annotations modified elsewhere
- Warns user with option to reload

### Browser Close
- Warns if unsaved changes exist
- Offers option to save before closing

## Performance

- **Video Streaming**: Instant playback via signed URLs
- **Autosave**: 2s debounce prevents excessive saves
- **API Caching**: SWR caches video list (30s refresh)
- **Parallel Loading**: Videos and annotations load concurrently

## Security

- **No keys in code**: Uses Application Default Credentials
- **Signed URLs**: Expire after 1 hour, auto-regenerate
- **Path validation**: API routes prevent directory traversal
- **Private bucket**: All access via signed URLs

## Troubleshooting

### "Failed to list videos"
- Check GCS authentication: `gcloud auth application-default login`
- Verify GCS path exists: `gsutil ls gs://buildai-dataset/finetune_dataset/test/`
- Check project permissions

### "Save failed"
- Check network connection
- Verify GCS write permissions
- Look for API errors in browser console

### "Annotations not loading"
- Verify .jsonl file exists in GCS
- Check file format (valid JSON)
- Look for API errors in browser console

### Videos not appearing
- Verify GCS path is correct
- Check file extensions (.mp4, .mov, .avi, .mkv, .webm)
- Ensure files are in the root of the specified path

## Development

### Local Testing
1. Auth: `gcloud auth application-default login`
2. Run: `npm run dev`
3. Open: `http://localhost:3000`

### Adding New Features
- GCS client: `lib/gcs-client.ts`
- API routes: `app/api/gcs/*/route.ts`
- Frontend: `components/*`

### Debugging
- Browser console for frontend errors
- Terminal for API/backend errors
- Network tab for API call inspection

## Future Enhancements

- Thumbnail generation for video previews
- Batch export all annotations
- Collaboration features (shared annotations)
- Video playback speed control
- Custom schemas per project
- Search/filter annotations by label

---

**Status**: ✅ Fully Implemented & Production Ready

All features tested locally. Ready for deployment and team use.
