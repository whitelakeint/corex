<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Admin-tunable signals that the bot couldn't answer. bot_id NULL = global
 * (applies to every bot). The Python runtime reads active rows to detect
 * unanswered questions in transcripts.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('deflection_phrases', function (Blueprint $table) {
            $table->id();
            $table->foreignId('bot_id')->nullable()->constrained('bots')->cascadeOnDelete();
            $table->string('phrase');
            $table->string('match_type', 20)->default('contains'); // contains | regex
            $table->boolean('active')->default(true);
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('deflection_phrases');
    }
};
