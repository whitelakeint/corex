@extends('layouts.app')

@section('content')
  <div class="card">
    <h2 style="margin-top:0">Bots</h2>
    <table>
      <thead>
        <tr><th>Bot</th><th>Property</th><th>Slug (BOT_ID)</th><th>Conversations</th><th>Pending questions</th></tr>
      </thead>
      <tbody>
        @forelse ($bots as $bot)
          <tr>
            <td>{{ $bot->name }}</td>
            <td>{{ $bot->property_name }}</td>
            <td><code>{{ $bot->slug }}</code></td>
            <td>{{ $bot->conversations_count }}</td>
            <td>
              <a href="{{ route('questions.index', ['bot_id' => $bot->id]) }}">
                {{ $bot->pending_count }}
              </a>
            </td>
          </tr>
        @empty
          <tr><td colspan="5" class="muted">No bots yet. Run the seeder or let a conversation register one.</td></tr>
        @endforelse
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2 style="margin-top:0">Latest unanswered questions</h2>
    <table>
      <thead><tr><th>Bot</th><th>Question</th><th></th></tr></thead>
      <tbody>
        @forelse ($recent as $q)
          <tr>
            <td>{{ $q->bot->name ?? '—' }}</td>
            <td>{{ \Illuminate\Support\Str::limit($q->question, 90) }}</td>
            <td><a href="{{ route('questions.show', $q) }}">Review →</a></td>
          </tr>
        @empty
          <tr><td colspan="3" class="muted">Nothing pending. 🎉</td></tr>
        @endforelse
      </tbody>
    </table>
  </div>
@endsection
