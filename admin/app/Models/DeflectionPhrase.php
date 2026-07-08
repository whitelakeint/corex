<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class DeflectionPhrase extends Model
{
    protected $fillable = ['bot_id', 'phrase', 'match_type', 'active'];

    protected $casts = ['active' => 'boolean'];

    public function bot(): BelongsTo
    {
        return $this->belongsTo(Bot::class);
    }
}
