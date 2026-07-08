<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasOne;

class UnansweredQuestion extends Model
{
    protected $fillable = [
        'bot_id', 'conversation_id', 'question', 'context_excerpt',
        'source', 'matched_phrase', 'status', 'dedup_hash',
    ];

    public function bot(): BelongsTo
    {
        return $this->belongsTo(Bot::class);
    }

    public function conversation(): BelongsTo
    {
        return $this->belongsTo(Conversation::class);
    }

    public function answer(): HasOne
    {
        return $this->hasOne(KnowledgeAnswer::class)->latestOfMany();
    }
}
