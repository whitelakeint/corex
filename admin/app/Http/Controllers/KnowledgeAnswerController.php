<?php

namespace App\Http\Controllers;

use App\Models\KnowledgeAnswer;
use App\Models\UnansweredQuestion;
use Illuminate\Http\Request;

class KnowledgeAnswerController extends Controller
{
    /** An expert writes/updates an answer and submits it for approval. */
    public function store(Request $request, UnansweredQuestion $question)
    {
        $data = $request->validate([
            'question' => ['required', 'string'],
            'answer'   => ['required', 'string'],
            'authored_by' => ['nullable', 'string', 'max:190'],
        ]);

        // One working answer per question — update if it exists, else create.
        $answer = KnowledgeAnswer::firstOrNew(['unanswered_question_id' => $question->id]);
        $answer->fill([
            'bot_id'      => $question->bot_id,
            'question'    => $data['question'],
            'answer'      => $data['answer'],
            'authored_by' => $data['authored_by'] ?? $answer->authored_by,
            'status'      => 'pending_approval',
        ])->save();

        $question->update(['status' => 'answered']);

        return redirect()
            ->route('questions.show', $question)
            ->with('status', 'Answer submitted for approval.');
    }
}
