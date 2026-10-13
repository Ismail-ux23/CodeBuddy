# Design decisions and later user changes

The initial pasted specification is preserved in `build-spec.md`. Its initial no-video rule was explicitly superseded by the user's later request: “i need video animation in hero section according tot he theme”.

The landing now contains an original 12-second local H.264 MP4 animation: a monochrome source constellation with silver orbital lines, nodes, and moving light points. Its black background blends into the page, and a baked fade keeps the headline area readable. There is no remote media URL, stock asset, WebGL, Three.js, or Lottie.

- Asset: `frontend/public/video/code-orbit-smooth.mp4` (960×540, 24 fps, optimized for smooth playback).
- Still fallback: `frontend/public/video/code-orbit-poster.png`.
- Editable generator: `frontend/scripts/video/hero-canvas.html`.
- Rendering command: `cd frontend && node scripts/video/render.mjs` (uses installed Chrome through Playwright).
- Playback is muted, looping, inline, and controlled by a keyboard-accessible pause/play button.
- Reduced-motion preference pauses video and disables ambient CSS motion.
- No source code or user data is used in the visual. It is decorative, not a visualization of a particular repository.

The React landing and standalone HTML reference share the same visual rules and local media. The standalone reference stores its video beside the HTML under `video/`. Its links target real application routes when served alongside the application.

After the user reported stuttering, the 1600×900 VP9 source was replaced with a 960×540 H.264 MP4. Full-page grain movement was disabled to reduce repaint work. The video is preloaded and still offers pause/reduced-motion behavior.
