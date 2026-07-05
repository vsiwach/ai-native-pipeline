# Winning the Endpoint Game — deploy guide

A static site (index + three documents) protected by a passcode via Vercel Edge Middleware.
The passcode check runs on Vercel's servers — nobody can read the docs without it.

## 1. Set your passcode
Open `middleware.js` and change the first line:

    const PASSCODE = 'endpoint-2026';

## 2. Deploy (5 minutes)
Requires Node.js installed.

    npm i -g vercel
    cd vercel-deploy
    vercel --prod

Accept the defaults ("no framework / other"). Vercel prints your live URL, e.g.
`https://endpoint-game.vercel.app`.

## 3. Share
Send Eric the URL and the passcode. The unlock lasts 7 days per browser (cookie).

## Notes
- Each document prints cleanly to PDF (Cmd+P).
- Alternative without middleware: Vercel Pro has built-in "Password Protection"
  under Project Settings → Deployment Protection — you can delete middleware.js if you use that.
- Files: index.html (hub), brief.html, strategy.html, prd.html, support.js, doc-page.js.


## Contents (updated)
- index.html — hub with tabs: OVERVIEW / DECK / BRIEF / STRATEGY / PRD / MVP / DEMO
- mvp.html — the MVP document (04), same doc style, prints to PDF
- demo.html — interactive migration console (05). With no backend it
  auto-switches to labeled MOCK MODE; append ?router=https://<your-router>
  to drive it live during the real demo. certs/latest.json is a real
  ed25519-signed certificate produced by tools/certify.py.
- Reading order: Deck -> Brief -> Strategy -> PRD -> MVP -> Demo.
The passcode middleware covers the new pages automatically (matcher: /(.*)).
