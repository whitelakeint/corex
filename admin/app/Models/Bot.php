<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Bot extends Model
{
    protected $fillable = [
        'slug', 'name', 'property_name', 'address',
        'tavus_persona_id', 'tavus_replica_id', 'kb_base_context', 'active',
    ];

    protected $casts = ['active' => 'boolean'];

    public function conversations(): HasMany
    {
        return $this->hasMany(Conversation::class);
    }

    public function unansweredQuestions(): HasMany
    {
        return $this->hasMany(UnansweredQuestion::class);
    }

    public function knowledgeAnswers(): HasMany
    {
        return $this->hasMany(KnowledgeAnswer::class);
    }

    public function deflectionPhrases(): HasMany
    {
        return $this->hasMany(DeflectionPhrase::class);
    }
}
