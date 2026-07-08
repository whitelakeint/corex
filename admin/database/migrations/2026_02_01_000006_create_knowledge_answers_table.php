<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Expert answers to unanswered questions. Flow:
 *   draft -> pending_approval -> approved/published (or rejected).
 * On publish, TavusPublisher rebuilds the bot's persona context from all
 * published answers and PATCHes it to Tavus.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('knowledge_answers', function (Blueprint $table) {
            $table->id();
            $table->foreignId('unanswered_question_id')->nullable()
                  ->constrained('unanswered_questions')->nullOnDelete();
            $table->foreignId('bot_id')->constrained('bots')->cascadeOnDelete();
            $table->longText('question');   // editable copy used for KB rendering
            $table->longText('answer');
            $table->string('authored_by', 190)->nullable();
            $table->string('status', 40)->default('draft'); // draft|pending_approval|approved|rejected|published
            $table->string('reviewed_by', 190)->nullable();
            $table->string('reject_reason')->nullable();
            $table->timestamp('approved_at')->nullable();
            $table->timestamp('published_at')->nullable();
            $table->timestamps();
            $table->index(['bot_id', 'status']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('knowledge_answers');
    }
};
