<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('unanswered_questions', function (Blueprint $table) {
            $table->id();
            $table->foreignId('bot_id')->constrained('bots')->cascadeOnDelete();
            $table->foreignId('conversation_id')->nullable()->constrained('conversations')->nullOnDelete();
            $table->longText('question');
            $table->longText('context_excerpt')->nullable();
            $table->string('source', 40);              // deflection_phrase | escalation
            $table->string('matched_phrase')->nullable();
            $table->string('status', 40)->default('pending'); // pending|answered|approved|rejected|published
            $table->string('dedup_hash', 64);
            $table->timestamps();
            $table->unique(['bot_id', 'dedup_hash']);
            $table->index(['bot_id', 'status']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('unanswered_questions');
    }
};
