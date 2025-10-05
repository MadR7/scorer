gcloud # Quick Start - Video Annotator

## ⚡ 3 Steps to Start

```bash
cd /Users/madhavrapelli/Documents/Projects/BuildAI/finetune/web-labeler
npm run dev
# Open: http://localhost:3000
```

## 🎬 How to Use

1. Click **"Load Video"** → Select any video file
2. Press **I** at start of action, **O** at end
3. Fill in **Label** and **Description**
4. Press **Enter** to commit
5. Repeat 2-4 for all segments
6. Click **"Export JSONL"** when done

## 🎹 Essential Shortcuts

- `I` = Mark IN (green)
- `O` = Mark OUT (blue)
- `Space` = Play/Pause
- `← →` = Seek 1s
- `Enter` = Commit segment
- `Cmd+Z` = Undo

## 📦 Output

Exports to JSONL:
```jsonl
{"video":"video.mp4","start":"1.23","end":"4.56","label":"pick_item","description":"..."}
```

## ✨ Why This Is Better

**Old Qt App**:
- Complex setup
- Platform issues
- Import errors
- Buggy feel

**New Web App**:
- `npm run dev` and done
- Works everywhere
- Fast & clean
- Zero issues

---

**Your server is running at http://localhost:3000** 🚀

Open it in your browser and start annotating!
