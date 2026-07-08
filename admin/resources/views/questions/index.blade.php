@extends('layouts.app')

@section('content')
  <div class="card">
    <h2 style="margin-top:0">Unanswered Questions</h2>

    <form method="get" class="filters">
      <div>
        <select name="bot_id" onchange="this.form.submit()">
          <option value="">All bots</option>
          @foreach ($bots as $bot)
            <option value="{{ $bot->id }}" @selected(request('bot_id') == $bot->id)>{{ $bot->name }}</option>
          @endforeach
        </select>
      </div>
      <div>
        <select name="status" onchange="this.form.submit()">
          @foreach (['pending','answered','published','rejected','all'] as $s)
            <option value="{{ $s }}" @selected($status === $s)>{{ ucfirst($s) }}</option>
          @endforeach
        </select>
      </div>
    </form>

    <table>
      <thead>
        <tr><th>Bot</th><th>Question</th><th>Source</th><th>Status</th><th></th></tr>
      </thead>
      <tbody>
        @forelse ($questions as $q)
          <tr>
            <td>{{ $q->bot->name ?? '—' }}</td>
            <td>{{ \Illuminate\Support\Str::limit($q->question, 90) }}</td>
            <td class="muted">{{ $q->matched_phrase ? '“'.\Illuminate\Support\Str::limit($q->matched_phrase, 30).'”' : $q->source }}</td>
            <td><span class="badge {{ $q->status }}">{{ $q->status }}</span></td>
            <td><a href="{{ route('questions.show', $q) }}">Review →</a></td>
          </tr>
        @empty
          <tr><td colspan="5" class="muted">No questions match this filter.</td></tr>
        @endforelse
      </tbody>
    </table>

    <div style="margin-top:1rem">{{ $questions->links() }}</div>
  </div>
@endsection
