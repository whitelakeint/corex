<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class KnowledgeAnswer extends Model
{
    protected $fillable = [
        'unanswered_question_id', 'bot_id', 'question', 'answer',
        'authored_by', 'status', 'reviewed_by', 'reject_reason',
        'approved_at', 'published_at',
    ];

    protected $casts = [
        'approved_at' => 'datetime',
        'published_at' => 'datetime',
    ];

    public function bot(): BelongsTo
    {
        return $this->belongsTo(Bot::class);
    }

    public function unansweredQuestion(): BelongsTo
    {
        return $this->belongsTo(UnansweredQuestion::class);
    }
}
