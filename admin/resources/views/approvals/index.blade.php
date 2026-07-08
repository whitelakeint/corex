@extends('layouts.app')

@section('content')
  <div class="card">
    <h2 style="margin-top:0">Answers awaiting approval</h2>
    <p class="muted">Approving publishes the answer into the bot's Tavus knowledge base (persona context).</p>

    @forelse ($answers as $answer)
      <div class="card" style="background:#faf8f4">
        <p class="muted">
          Bot: <strong>{{ $answer->bot->name ?? '—' }}</strong>
          @if ($answer->authored_by) · by {{ $answer->authored_by }} @endif
        </p>
        <label>Q</label>
        <div>{{ $answer->question }}</div>
        <label>A</label>
        <div>{{ $answer->answer }}</div>

        <div style="display:flex; gap:.75rem; margin-top:1rem; flex-wrap:wrap">
          <form method="post" action="{{ route('approvals.approve', $answer) }}" style="display:flex; gap:.5rem; align-items:center">
            @csrf
            <input type="text" name="reviewed_by" placeholder="Reviewer name">
            <button class="btn" type="submit">Approve &amp; publish</button>
          </form>
          <form method="post" action="{{ route('approvals.reject', $answer) }}" style="display:flex; gap:.5rem; align-items:center">
            @csrf
            <input type="text" name="reject_reason" placeholder="Reason (optional)">
            <button class="btn danger" type="submit">Reject</button>
          </form>
        </div>
      </div>
    @empty
      <p class="muted">Nothing awaiting approval.</p>
    @endforelse

    <div style="margin-top:1rem">{{ $answers->links() }}</div>
  </div>
@endsection
