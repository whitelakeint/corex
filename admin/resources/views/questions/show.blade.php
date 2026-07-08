@extends('layouts.app')

@section('content')
  <div class="card">
    <p class="muted"><a href="{{ route('questions.index') }}">← Back to queue</a></p>
    <h2 style="margin-top:0">Unanswered question</h2>
    <p class="muted">
      Bot: <strong>{{ $question->bot->name ?? '—' }}</strong> ·
      Detected via: {{ $question->matched_phrase ? '“'.$question->matched_phrase.'”' : $question->source }} ·
      <span class="badge {{ $question->status }}">{{ $question->status }}</span>
    </p>

    <label>Visitor asked</label>
    <div class="transcript"><strong>{{ $question->question }}</strong></div>

    @if ($question->conversation && $question->conversation->messages->isNotEmpty())
      <label>Conversation transcript</label>
      <div class="transcript">
        @foreach ($question->conversation->messages as $m)
          <div class="{{ $m->role }}"><strong>{{ ucfirst($m->role) }}:</strong> {{ $m->content }}</div>
        @endforeach
      </div>
    @endif
  </div>

  <div class="card">
    <h3 style="margin-top:0">Expert answer</h3>
    <form method="post" action="{{ route('answers.store', $question) }}">
      @csrf
      <label>Question (as it will be stored in the knowledge base)</label>
      <textarea name="question" rows="2">{{ old('question', $question->answer->question ?? $question->question) }}</textarea>

      <label>Answer</label>
      <textarea name="answer" rows="5" placeholder="Write the correct answer the bot should give…">{{ old('answer', $question->answer->answer ?? '') }}</textarea>

      <label>Your name (optional)</label>
      <input type="text" name="authored_by" value="{{ old('authored_by', $question->answer->authored_by ?? '') }}">

      <div style="margin-top:1rem">
        <button class="btn" type="submit">Submit for approval</button>
        @if ($question->answer)
          <span class="muted" style="margin-left:.75rem">
            Current answer status: <span class="badge {{ $question->answer->status }}">{{ $question->answer->status }}</span>
          </span>
        @endif
      </div>
    </form>
  </div>
@endsection
