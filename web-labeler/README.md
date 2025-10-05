# Video Annotator - Web Edition ⚡

A fast, clean, web-based video annotation tool built with Next.js. No Qt, no Python, no bullshit.

## Features

- ✅ **Blazing Fast**: Built with Next.js, runs in browser, no setup hell
- ✅ **Keyboard-Driven**: All shortcuts you need (I/O/Enter/J/K/L/Space/Arrows)
- ✅ **Visual Timeline**: See segments, markers, and playhead at a glance
- ✅ **JSONL Export**: One-click export to JSONL format
- ✅ **Dark Theme**: Beautiful, professional dark UI
- ✅ **Zero Config**: Just load a video and start annotating

## Quick Start

```bash
# Install
npm install

# Run
npm run dev

# Open browser
# http://localhost:3000
```

That's it. No virtual environments, no Qt bindings, no VLC plugins.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `I` | Mark IN point (green) |
| `O` | Mark OUT point (blue) |
| `Space` | Play / Pause |
| `←` / `→` | Seek 1 second |
| `Shift+←` / `→` | Seek 5 seconds |
| `J` | Play backward |
| `K` | Stop |
| `L` | Play fast forward |
| `Enter` | Commit segment (when form filled) |
| `Cmd/Ctrl+Z` | Undo last segment |

## Workflow

1. **Load Video**: Click "Load Video" button
2. **Mark Points**: Press `I` at start, `O` at end of segment
3. **Fill Form**: Select label, write description
4. **Commit**: Press Enter or click "Commit Segment"
5. **Export**: Click "Export JSONL" when done

## JSONL Output Format

```jsonl
{"video":"sample1.mp4","start":"2.34","end":"5.67","label":"pick_item","description":"Operator picks up item"}
{"video":"sample1.mp4","start":"5.67","end":"9.12","label":"align_item","description":"Operator aligns item"}
```

## Why Web?

**Before (Qt/Python RVSA)**:
- ❌ Complex setup (venv, Qt, VLC, dependencies)
- ❌ Platform-specific issues
- ❌ Import errors, plugin hell
- ❌ Slow iteration

**After (Next.js Web)**:
- ✅ `npm install && npm run dev`
- ✅ Works everywhere (Mac, Windows, Linux, even mobile)
- ✅ Zero platform issues
- ✅ Fast, clean, simple

## Tech Stack

- **Next.js 15**: React framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **HTML5 Video**: Native video playback
- **Canvas API**: Timeline rendering

No external video libraries, no bloat, just modern web APIs.

## Development

```bash
# Install
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Deployment

Deploy anywhere:
- Vercel (one-click)
- Netlify
- Any static host
- Even localhost

## License

MIT

---

**Built in 10 minutes. Works everywhere. Zero bullshit.** ⚡