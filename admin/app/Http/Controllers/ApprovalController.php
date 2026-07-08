<?php

namespace App\Http\Controllers;

use App\Models\KnowledgeAnswer;
use App\Services\TavusPublisher;
use Illuminate\Http\Request;

class ApprovalController extends Controller
{
    /** Reviewer queue: answers awaiting approval. */
    public function index()
    {
        $answers = KnowledgeAnswer::with(['bot', 'unansweredQuestion'])
            ->where('status', 'pending_approval')
            ->latest()
            ->paginate(20);

        return view('approvals.index', compact('answers'));
    }

    /** Approve -> mark published, then push the bot's KB to Tavus. */
    public function approve(Request $request, KnowledgeAnswer $answer, TavusPublisher $publisher)
    {
        $data = $request->validate(['reviewed_by' => ['nullable', 'string', 'max:190']]);

        $answer->update([
            'status'       => 'published',
            'reviewed_by'  => $data['reviewed_by'] ?? null,
            'approved_at'  => now(),
            'published_at' => now(),
        ]);

        if ($answer->unansweredQuestion) {
            $answer->unansweredQuestion->update(['status' => 'published']);
        }

        // Rebuild + PATCH the persona context (base + all published answers).
        $result = $publisher->publish($answer->bot);

        return redirect()->route('approvals.index')->with(
            'status',
            $result['ok']
                ? 'Approved and published to the bot knowledge base.'
                : 'Approved, but publishing to Tavus failed: ' . ($result['error'] ?? 'unknown error')
        );
    }

    /** Reject with a reason; the question returns to the queue for a new answer. */
    public function reject(Request $request, KnowledgeAnswer $answer)
    {
        $data = $request->validate([
            'reject_reason' => ['nullable', 'string', 'max:255'],
            'reviewed_by'   => ['nullable', 'string', 'max:190'],
        ]);

        $answer->update([
            'status'        => 'rejected',
            'reject_reason' => $data['reject_reason'] ?? null,
            'reviewed_by'   => $data['reviewed_by'] ?? null,
        ]);

        if ($answer->unansweredQuestion) {
            $answer->unansweredQuestion->update(['status' => 'pending']);
        }

        return redirect()->route('approvals.index')->with('status', 'Answer rejected.');
    }
}
