# GCS Setup for Local Development

## Issue: Signed URL Generation with ADC

When using `gcloud auth application-default login`, signed URLs fail because user credentials don't include service account email.

## Solutions

### Option 1: Enable IAM SignBlob (Recommended for Production)

Grant your user account permission to sign URLs:

```bash
# Get your email
gcloud auth list

# Grant token creator role (replace YOUR_EMAIL)
gcloud projects add-iam-policy-binding data-470400 \
  --member="user:YOUR_EMAIL@gmail.com" \
  --role="roles/iam.serviceAccountTokenCreator"
```

### Option 2: Use Service Account (For Production Deployment)

1. Create a service account:
```bash
gcloud iam service-accounts create video-labeler \
  --display-name="Video Labeler Service Account"
```

2. Grant permissions:
```bash
gcloud projects add-iam-policy-binding data-470400 \
  --member="serviceAccount:video-labeler@data-470400.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

3. Create and download key:
```bash
gcloud iam service-accounts keys create ~/video-labeler-key.json \
  --iam-account=video-labeler@data-470400.iam.gserviceaccount.com
```

4. Set environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS=~/video-labeler-key.json
```

### Option 3: Public Bucket Access (Quick Fix for Dev)

Make the bucket publicly readable (⚠️ use with caution):

```bash
# Set CORS
echo '[
  {
    "origin": ["http://localhost:3000"],
    "method": ["GET"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]' > cors.json

gsutil cors set cors.json gs://buildai-dataset

# Make files publicly readable (ONLY for dev!)
gsutil iam ch allUsers:objectViewer gs://buildai-dataset
```

## Current Implementation

The app now falls back to public URLs if signed URL generation fails. This works if:
- Bucket has CORS configured for localhost
- Files are publicly readable OR
- User has direct read access

## Testing

After setup, the error should disappear and videos should stream correctly.

```bash
# Refresh the page
# Videos should now load
```
