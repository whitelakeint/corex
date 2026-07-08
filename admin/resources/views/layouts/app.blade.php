<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Core X — Knowledge Admin</title>
  <style>
    :root { --primary:#1a3a5c; --accent:#c9a96e; --bg:#f5f3ef; --line:#e4e0d8; --muted:#6b6b6b; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:"Segoe UI",system-ui,sans-serif; background:var(--bg); color:#222; }
    header { background:var(--primary); color:#fff; padding:1rem 1.5rem; display:flex; align-items:center; gap:1.5rem; }
    header h1 { font-size:1.1rem; margin:0; }
    header nav a { color:#fff; text-decoration:none; opacity:.8; margin-right:1rem; font-size:.9rem; }
    header nav a:hover { opacity:1; }
    main { max-width:1000px; margin:1.5rem auto; padding:0 1.25rem; }
    .card { background:#fff; border:1px solid var(--line); border-radius:8px; padding:1.25rem; margin-bottom:1.25rem; }
    table { width:100%; border-collapse:collapse; }
    th, td { text-align:left; padding:.6rem .5rem; border-bottom:1px solid var(--line); font-size:.9rem; vertical-align:top; }
    th { color:var(--muted); font-weight:600; font-size:.75rem; text-transform:uppercase; letter-spacing:.04em; }
    a { color:var(--primary); }
    .badge { display:inline-block; padding:.15rem .5rem; border-radius:999px; font-size:.7rem; font-weight:700; text-transform:uppercase; }
    .badge.pending { background:#fff3d6; color:#8a6d00; }
    .badge.answered { background:#dbeafe; color:#1e40af; }
    .badge.published { background:#dcfce7; color:#166534; }
    .badge.rejected { background:#fee2e2; color:#991b1b; }
    .btn { display:inline-block; background:var(--primary); color:#fff; border:none; border-radius:6px; padding:.5rem 1rem; font-size:.85rem; cursor:pointer; text-decoration:none; }
    .btn.secondary { background:#e8e8e8; color:#222; }
    .btn.danger { background:#b91c1c; }
    textarea, input[type=text] { width:100%; padding:.6rem; border:1px solid var(--line); border-radius:6px; font-family:inherit; font-size:.9rem; }
    label { display:block; font-size:.8rem; color:var(--muted); margin:.75rem 0 .25rem; font-weight:600; }
    .flash { background:#dcfce7; border:1px solid #86efac; color:#166534; padding:.75rem 1rem; border-radius:6px; margin-bottom:1rem; }
    .muted { color:var(--muted); font-size:.85rem; }
    .transcript { background:#faf8f4; border:1px solid var(--line); border-radius:6px; padding:.75rem; max-height:320px; overflow:auto; font-size:.85rem; }
    .transcript .visitor { color:#1e40af; }
    .transcript .assistant { color:#166534; }
    .filters { display:flex; gap:.75rem; align-items:center; margin-bottom:1rem; flex-wrap:wrap; }
    select { padding:.45rem; border:1px solid var(--line); border-radius:6px; }
  </style>
</head>
<body>
  <header>
    <h1>Core X · Knowledge Admin</h1>
    <nav>
      <a href="{{ route('dashboard') }}">Dashboard</a>
      <a href="{{ route('questions.index') }}">Unanswered Questions</a>
      <a href="{{ route('approvals.index') }}">Approvals</a>
    </nav>
  </header>
  <main>
    @if (session('status'))
      <div class="flash">{{ session('status') }}</div>
    @endif
    @yield('content')
  </main>
</body>
</html>
