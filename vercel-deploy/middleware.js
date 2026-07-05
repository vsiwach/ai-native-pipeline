// Edge Middleware — passcode gate for the whole site.
// CHANGE THE PASSCODE HERE before deploying:
const PASSCODE = 'endpoint-2026';

const GATE_HTML = "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n<title>Protected — Modular</title>\n<link href=\"https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap\" rel=\"stylesheet\">\n<style>\n  body { margin:0; background:#16160F; color:#F4F4EE; font-family:'Archivo',sans-serif; min-height:100vh; display:flex; align-items:center; justify-content:center; }\n  .card { width:min(420px, 90vw); }\n  .rule { height:2px; background:#F4F4EE; margin-top:12px; }\n  .mono { font-family:'IBM Plex Mono',monospace; letter-spacing:.14em; font-size:11px; }\n  h1 { font-size:34px; font-weight:800; letter-spacing:-.02em; line-height:1.05; margin:34px 0 0; }\n  h1 span { color:#D5F26E; }\n  p { color:#A8A89E; font-size:14px; line-height:1.55; margin:14px 0 0; }\n  form { display:flex; gap:10px; margin-top:28px; }\n  input { flex:1; background:#1D1D15; border:1px solid #3A3A32; color:#F4F4EE; padding:12px 14px; font-family:'IBM Plex Mono',monospace; font-size:14px; outline:none; }\n  input:focus { border-color:#D5F26E; }\n  button { background:#D5F26E; color:#16160F; border:none; padding:12px 20px; font-family:'IBM Plex Mono',monospace; font-weight:600; font-size:12px; letter-spacing:.08em; cursor:pointer; }\n  button:hover { background:#C6E96A; }\n  .err { color:#E08A5B; font-family:'IBM Plex Mono',monospace; font-size:11px; letter-spacing:.06em; margin-top:12px; display:__ERR__; }\n</style></head>\n<body><div class=\"card\">\n  <div class=\"mono\" style=\"display:flex;justify-content:space-between;\"><span style=\"font-weight:600;\">MODULAR</span><span style=\"color:#8A8A80;\">CONFIDENTIAL</span></div>\n  <div class=\"rule\"></div>\n  <h1>Winning the <span>endpoint game</span></h1>\n  <p>These documents are passcode-protected. Enter the code you were given.</p>\n  <form method=\"GET\" action=\"__ACTION__\"><input type=\"hidden\" name=\"h\"><input type=\"password\" name=\"code\" placeholder=\"passcode\" autofocus autocomplete=\"off\"><button type=\"submit\">ENTER</button></form>\n  <div class=\"err\">Incorrect passcode — try again.</div>\n</div>\n<script>document.querySelector('input[name=h]').value = location.hash.slice(1);</script>\n</body></html>";

export const config = { matcher: '/(.*)' };

export default function middleware(request) {
  const url = new URL(request.url);

  // Already unlocked?
  const cookies = request.headers.get('cookie') || '';
  if (cookies.split(/;\s*/).some((c) => c === 'docs_key=' + encodeURIComponent(PASSCODE))) {
    return; // continue to the requested file
  }

  // Correct code submitted? (`h` carries the pre-gate fragment — e.g. the
  // hub's #demo tab — because a form submission drops location.hash)
  const code = url.searchParams.get('code');
  if (code === PASSCODE) {
    url.searchParams.delete('code');
    const hash = url.searchParams.get('h') || '';
    url.searchParams.delete('h');
    return new Response(null, {
      status: 302,
      headers: {
        Location: url.pathname + url.search +
          (/^[\w-]{1,32}$/.test(hash) ? '#' + hash : ''),
        'Set-Cookie':
          'docs_key=' + encodeURIComponent(PASSCODE) +
          '; Path=/; Max-Age=604800; HttpOnly; Secure; SameSite=Lax',
      },
    });
  }

  // Otherwise show the gate (with an error note if a wrong code was tried)
  const html = GATE_HTML
    .replace('__ACTION__', url.pathname)
    .replace('__ERR__', code === null ? 'none' : 'block');
  return new Response(html, {
    status: 401,
    headers: { 'Content-Type': 'text/html; charset=utf-8' },
  });
}
