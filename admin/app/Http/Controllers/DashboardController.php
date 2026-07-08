<?php

namespace App\Http\Controllers;

use App\Models\Bot;
use App\Models\UnansweredQuestion;

class DashboardController extends Controller
{
    public function index()
    {
        $bots = Bot::withCount([
            'conversations',
            'unansweredQuestions as pending_count' => fn ($q) => $q->where('status', 'pending'),
        ])->orderBy('name')->get();

        $recent = UnansweredQuestion::with('bot')
            ->where('status', 'pending')
            ->latest()
            ->limit(10)
            ->get();

        return view('dashboard', compact('bots', 'recent'));
    }
}
