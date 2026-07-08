<?php

namespace App\Http\Controllers;

use App\Models\Bot;
use App\Models\UnansweredQuestion;
use Illuminate\Http\Request;

class UnansweredQuestionController extends Controller
{
    /** Queue of questions the bot couldn't answer, filterable by bot + status. */
    public function index(Request $request)
    {
        $bots = Bot::orderBy('name')->get();
        $status = $request->query('status', 'pending');

        $questions = UnansweredQuestion::with(['bot', 'answer'])
            ->when($request->filled('bot_id'), fn ($q) => $q->where('bot_id', $request->query('bot_id')))
            ->when($status !== 'all', fn ($q) => $q->where('status', $status))
            ->latest()
            ->paginate(20)
            ->withQueryString();

        return view('questions.index', compact('questions', 'bots', 'status'));
    }

    /** One question with its source conversation transcript + answer form. */
    public function show(UnansweredQuestion $question)
    {
        $question->load(['bot', 'answer', 'conversation.messages']);

        return view('questions.show', compact('question'));
    }
}
